"""
PDF upload routes for trade extraction.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app import db
from app.models import Purchase, PdfUploadLog
from app.services.pdf_extractor import extract_trades_from_pdf
from app.services.stock_data import validate_ticker, is_trading_day, invalidate_price_cache

pdf_upload_bp = Blueprint('pdf_upload', __name__)

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_upload_count_today(user_id: int) -> int:
    """Get the number of PDF uploads for a user today (UTC)."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    return PdfUploadLog.query.filter(
        PdfUploadLog.user_id == user_id,
        PdfUploadLog.uploaded_at >= today_start
    ).count()


def _get_next_reset_time_iso() -> str:
    """Get the ISO timestamp for when the quota resets (midnight UTC)."""
    tomorrow = date.today() + timedelta(days=1)
    reset_time = datetime.combine(tomorrow, datetime.min.time())
    return reset_time.isoformat() + 'Z'


@pdf_upload_bp.route('/uploads/pdf/quota', methods=['GET'])
@login_required
def get_upload_quota():
    """
    Get the user's remaining PDF upload quota for today.

    Response: {
        used: number,
        limit: number | null,
        remaining: number | null,
        resets_at: string (ISO datetime),
        is_premium: boolean
    }
    """
    # Premium users have unlimited uploads
    if current_user.is_premium:
        return jsonify({
            'used': 0,
            'limit': None,
            'remaining': None,
            'resets_at': _get_next_reset_time_iso(),
            'is_premium': True
        }), 200

    limit = current_app.config.get('PDF_DAILY_UPLOAD_LIMIT', 3)
    used = get_user_upload_count_today(current_user.id)
    remaining = max(0, limit - used)

    return jsonify({
        'used': used,
        'limit': limit,
        'remaining': remaining,
        'resets_at': _get_next_reset_time_iso(),
        'is_premium': False
    }), 200


@pdf_upload_bp.route('/uploads/pdf/extract', methods=['POST'])
@login_required
def extract_trades():
    """
    Upload a PDF and extract trade data using OpenAI Vision.
    Returns extracted trades for user confirmation.

    Request: multipart/form-data with 'file' field
    Response: {trades: [...], total_pages: N, notes: [...]}
    """
    # Check daily upload limit FIRST (before any processing) - skip for premium users
    if not current_user.is_premium:
        limit = current_app.config.get('PDF_DAILY_UPLOAD_LIMIT', 3)
        used = get_user_upload_count_today(current_user.id)

        if used >= limit:
            return jsonify({
                'error': 'Daily upload limit reached',
                'code': 'QUOTA_EXCEEDED',
                'show_upgrade': True,
                'quota': {
                    'used': used,
                    'limit': limit,
                    'remaining': 0,
                    'resets_at': _get_next_reset_time_iso()
                }
            }), 429

    # Log this upload attempt IMMEDIATELY (counts toward limit)
    upload_log = PdfUploadLog(user_id=current_user.id)
    db.session.add(upload_log)
    db.session.commit()

    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Check if file was selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDF files are allowed'}), 400

    # Check file size
    file.seek(0, 2)  # Seek to end of file
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': f'File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB'}), 400

    if file_size == 0:
        return jsonify({'error': 'File is empty'}), 400

    try:
        # Extract trades from PDF using the pdf_extractor service
        # Read the file content as bytes (file is reset to beginning after size check)
        pdf_bytes = file.read()
        extraction_result = extract_trades_from_pdf(pdf_bytes)

        # Check if extraction had critical errors (no trades and errors present)
        errors = extraction_result.get('errors', [])
        if errors and not extraction_result.get('trades'):
            error_message = '; '.join(errors) if errors else 'Failed to extract trades from PDF'
            return jsonify({'error': error_message}), 500

        trades = extraction_result.get('trades', [])
        total_pages = extraction_result.get('total_pages', 0)
        notes = extraction_result.get('notes', [])

        # Validate each extracted trade
        validated_trades = []
        for trade in trades:
            validation = validate_extracted_trade(trade)
            trade['validation'] = validation
            validated_trades.append(trade)

        return jsonify({
            'trades': validated_trades,
            'total_pages': total_pages,
            'notes': notes
        }), 200

    except ValueError as e:
        # Handle configuration errors (like missing API key)
        error_msg = str(e)
        if 'OPENAI_API_KEY' in error_msg:
            return jsonify({'error': 'PDF extraction is not configured. Please contact the administrator.'}), 503
        current_app.logger.error(f"Value error extracting trades from PDF: {e}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        current_app.logger.error(f"Error extracting trades from PDF: {e}")
        return jsonify({'error': 'An error occurred while processing the PDF'}), 500


def validate_extracted_trade(trade: dict) -> dict:
    """
    Validate an extracted trade.
    Returns {valid: bool, warnings: [...], errors: [...]}
    """
    errors = []
    warnings = []

    # Check required fields
    required_fields = ['ticker', 'purchase_date', 'quantity', 'price_per_share']
    for field in required_fields:
        if field not in trade or trade[field] is None:
            errors.append(f'Missing required field: {field}')

    if errors:
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    # Validate ticker
    ticker = trade.get('ticker', '').upper().strip()
    if not ticker:
        errors.append('Ticker symbol is empty')
    elif len(ticker) > 10:
        errors.append('Ticker symbol is too long (max 10 characters)')
    else:
        # Check if ticker exists (can be slow, so we do basic validation first)
        if not validate_ticker(ticker):
            errors.append(f'Invalid or unknown ticker symbol: {ticker}')

    # Validate purchase date
    try:
        purchase_date_str = trade.get('purchase_date', '')
        if isinstance(purchase_date_str, str):
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        else:
            purchase_date = purchase_date_str

        # Check if date is not in the future
        today = datetime.now().date()
        if purchase_date > today:
            errors.append('Purchase date cannot be in the future')

        # Check if it's a trading day
        if not errors and not is_trading_day(purchase_date):
            warnings.append('Purchase date is not a valid trading day (weekend or holiday)')

    except (ValueError, TypeError, AttributeError):
        errors.append('Invalid date format. Expected YYYY-MM-DD')

    # Validate quantity
    try:
        quantity = float(trade.get('quantity', 0))
        if quantity <= 0:
            errors.append('Quantity must be positive')
        elif quantity > 1000000:
            warnings.append('Unusually large quantity detected')
    except (ValueError, TypeError):
        errors.append('Quantity must be a valid number')

    # Validate price per share
    try:
        price_per_share = float(trade.get('price_per_share', 0))
        if price_per_share <= 0:
            errors.append('Price per share must be positive')
        elif price_per_share > 100000:
            warnings.append('Unusually high price per share detected')
    except (ValueError, TypeError):
        errors.append('Price per share must be a valid number')

    # Calculate and validate total amount
    if not errors:
        try:
            quantity = float(trade.get('quantity', 0))
            price_per_share = float(trade.get('price_per_share', 0))
            total_amount = quantity * price_per_share

            if total_amount > 10000000:
                warnings.append('Unusually large total amount detected')
        except (ValueError, TypeError):
            pass  # Already captured in previous validations

    is_valid = len(errors) == 0

    return {
        'valid': is_valid,
        'errors': errors,
        'warnings': warnings
    }


@pdf_upload_bp.route('/uploads/pdf/confirm', methods=['POST'])
@login_required
def confirm_trades():
    """
    Save confirmed trades to the user's account.

    Request: {trades: [{ticker, purchase_date, quantity, price_per_share}, ...]}
    Response: {saved: N, total: N, errors: [...]}
    """
    # Get JSON body
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'trades' not in data:
        return jsonify({'error': 'Missing trades array'}), 400

    trades = data.get('trades', [])

    if not isinstance(trades, list):
        return jsonify({'error': 'Trades must be an array'}), 400

    if len(trades) == 0:
        return jsonify({'error': 'No trades to save'}), 400

    if len(trades) > 100:
        return jsonify({'error': 'Maximum 100 trades can be saved at once'}), 400

    saved_count = 0
    total_count = len(trades)
    errors = []

    for idx, trade in enumerate(trades):
        try:
            # Validate required fields
            if not all(k in trade for k in ['ticker', 'purchase_date', 'quantity', 'price_per_share']):
                errors.append(f'Trade {idx + 1}: Missing required fields')
                continue

            ticker = trade['ticker'].upper().strip()

            # Parse and validate date
            try:
                purchase_date = datetime.strptime(trade['purchase_date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                errors.append(f'Trade {idx + 1}: Invalid date format')
                continue

            # Validate and convert quantity
            try:
                quantity = float(trade['quantity'])
                if quantity <= 0:
                    errors.append(f'Trade {idx + 1}: Quantity must be positive')
                    continue
            except (ValueError, TypeError):
                errors.append(f'Trade {idx + 1}: Invalid quantity')
                continue

            # Validate and convert price
            try:
                price_per_share = float(trade['price_per_share'])
                if price_per_share <= 0:
                    errors.append(f'Trade {idx + 1}: Price per share must be positive')
                    continue
            except (ValueError, TypeError):
                errors.append(f'Trade {idx + 1}: Invalid price per share')
                continue

            # Calculate amount
            amount = quantity * price_per_share

            # Create Purchase record
            purchase = Purchase(
                user_id=current_user.id,
                ticker=ticker,
                purchase_date=purchase_date,
                amount=amount,
                shares_bought=quantity,
                price_at_purchase=price_per_share
            )

            db.session.add(purchase)
            saved_count += 1

        except Exception as e:
            current_app.logger.error(f"Error saving trade {idx + 1}: {e}")
            errors.append(f'Trade {idx + 1}: Failed to save - {str(e)}')

    # Commit all successful purchases
    try:
        if saved_count > 0:
            db.session.commit()
            # Invalidate price cache to ensure fresh prices on next fetch
            invalidate_price_cache()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing trades to database: {e}")
        return jsonify({
            'error': 'Failed to save trades to database',
            'saved': 0,
            'total': total_count,
            'errors': errors
        }), 500

    status_code = 200 if saved_count == total_count else 207  # 207 = Multi-Status

    return jsonify({
        'saved': saved_count,
        'total': total_count,
        'errors': errors if errors else []
    }), status_code
