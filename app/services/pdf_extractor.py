"""
PDF trade extraction service using OpenAI GPT-4 Vision.
"""

import base64
import json
from datetime import datetime
from typing import Dict, List, Optional
import fitz  # PyMuPDF
from openai import OpenAI
from flask import current_app


class PDFTradeExtractor:
    """Extracts trade data from PDF documents using GPT-4 Vision."""

    EXTRACTION_PROMPT = """You are a financial document analyzer. Extract all stock BUY transactions from this brokerage statement or trade confirmation.

For each BUY trade, extract:
- ticker: Stock symbol (e.g., AAPL, TSLA)
- purchase_date: Date of the trade in YYYY-MM-DD format
- quantity: Number of shares bought (positive number)
- price_per_share: Price per share in USD
- total_amount: Total transaction amount in USD (optional)

Only extract BUY transactions, not sells.
Return a JSON object with a "trades" array. If no trades found, return {"trades": []}.
Be precise with numbers - do not round.

Example output:
{
    "trades": [
        {
            "ticker": "AAPL",
            "purchase_date": "2024-01-15",
            "quantity": 10.5,
            "price_per_share": 185.50,
            "total_amount": 1947.75
        }
    ],
    "notes": "Extracted from monthly statement"
}"""

    def __init__(self):
        self.client = None

    def _get_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self.client is None:
            api_key = current_app.config.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            self.client = OpenAI(api_key=api_key)
        return self.client

    def pdf_to_images(self, pdf_bytes: bytes) -> List[bytes]:
        """
        Convert PDF pages to PNG images.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            List of PNG image bytes, one per page

        Raises:
            ValueError: If PDF cannot be opened or is empty
        """
        try:
            # Open PDF from memory stream
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

            if pdf_document.page_count == 0:
                raise ValueError("PDF document is empty")

            images = []

            # Render each page at 2x resolution (144 DPI) for better OCR
            zoom = 2.0
            matrix = fitz.Matrix(zoom, zoom)

            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]

                # Render page to pixmap (image)
                pix = page.get_pixmap(matrix=matrix)

                # Convert to PNG bytes
                png_bytes = pix.tobytes("png")
                images.append(png_bytes)

            pdf_document.close()
            return images

        except Exception as e:
            raise ValueError(f"Failed to convert PDF to images: {str(e)}")

    def extract_trades_from_image(self, image_bytes: bytes) -> Dict:
        """
        Extract trades from a single image using GPT-4 Vision.

        Args:
            image_bytes: PNG image bytes

        Returns:
            Dict with 'trades' array and optional 'notes'

        Raises:
            ValueError: If API call fails or response is invalid
        """
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            client = self._get_client()

            # Call OpenAI GPT-4 Vision API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self.EXTRACTION_PROMPT
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=2000
            )

            # Parse JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Ensure trades array exists
            if "trades" not in result:
                result["trades"] = []

            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to extract trades from image: {str(e)}")

    def extract_trades_from_pdf(self, pdf_bytes: bytes) -> Dict:
        """
        Extract all trades from a PDF document.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Dict with:
                - trades: List of validated trade dicts
                - total_pages: Number of pages processed
                - notes: List of notes from extraction
                - errors: List of errors encountered (if any)
        """
        all_trades = []
        all_notes = []
        errors = []

        try:
            # Convert PDF to images
            images = self.pdf_to_images(pdf_bytes)
            total_pages = len(images)

            # Extract trades from each page
            for page_num, image_bytes in enumerate(images, start=1):
                try:
                    result = self.extract_trades_from_image(image_bytes)

                    # Collect trades
                    page_trades = result.get("trades", [])
                    all_trades.extend(page_trades)

                    # Collect notes
                    if "notes" in result:
                        all_notes.append(f"Page {page_num}: {result['notes']}")

                except Exception as e:
                    error_msg = f"Page {page_num}: {str(e)}"
                    errors.append(error_msg)
                    current_app.logger.warning(f"Failed to extract from page {page_num}: {e}")

            # Deduplicate trades
            unique_trades = self._deduplicate_trades(all_trades)

            # Validate and normalize trades
            validated_trades = self._validate_trades(unique_trades)

            return {
                "trades": validated_trades,
                "total_pages": total_pages,
                "notes": all_notes,
                "errors": errors if errors else None
            }

        except Exception as e:
            current_app.logger.error(f"PDF extraction failed: {e}")
            return {
                "trades": [],
                "total_pages": 0,
                "notes": [],
                "errors": [str(e)]
            }

    def _deduplicate_trades(self, trades: List[Dict]) -> List[Dict]:
        """
        Remove duplicate trades based on (ticker, date, quantity).

        Args:
            trades: List of trade dicts

        Returns:
            Deduplicated list of trades
        """
        seen = set()
        unique_trades = []

        for trade in trades:
            # Create unique key from ticker, date, and quantity
            ticker = trade.get("ticker", "").upper()
            date = trade.get("purchase_date", "")
            quantity = trade.get("quantity", 0)

            key = (ticker, date, quantity)

            if key not in seen and ticker and date and quantity:
                seen.add(key)
                unique_trades.append(trade)

        return unique_trades

    def _validate_trades(self, trades: List[Dict]) -> List[Dict]:
        """
        Validate and normalize trade data.

        Args:
            trades: List of trade dicts

        Returns:
            List of validated and normalized trades
        """
        validated = []

        for trade in trades:
            try:
                # Uppercase ticker
                ticker = trade.get("ticker", "").strip().upper()
                if not ticker:
                    continue

                # Parse and normalize date
                purchase_date = self._parse_date(trade.get("purchase_date", ""))
                if not purchase_date:
                    current_app.logger.warning(f"Invalid date for trade: {trade}")
                    continue

                # Validate positive numbers
                quantity = float(trade.get("quantity", 0))
                if quantity <= 0:
                    current_app.logger.warning(f"Invalid quantity for trade: {trade}")
                    continue

                price_per_share = float(trade.get("price_per_share", 0))
                if price_per_share <= 0:
                    current_app.logger.warning(f"Invalid price for trade: {trade}")
                    continue

                # Calculate total_amount if missing
                total_amount = trade.get("total_amount")
                if total_amount is None or total_amount == "":
                    total_amount = round(quantity * price_per_share, 2)
                else:
                    total_amount = float(total_amount)

                validated.append({
                    "ticker": ticker,
                    "purchase_date": purchase_date,
                    "quantity": quantity,
                    "price_per_share": price_per_share,
                    "total_amount": total_amount
                })

            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Failed to validate trade {trade}: {e}")
                continue

        return validated

    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string to YYYY-MM-DD format.

        Tries multiple common date formats.

        Args:
            date_str: Date string in various formats

        Returns:
            Date in YYYY-MM-DD format or None if parsing fails
        """
        if not date_str:
            return None

        # Common date formats to try
        formats = [
            "%Y-%m-%d",           # 2024-01-15
            "%m/%d/%Y",           # 01/15/2024
            "%m-%d-%Y",           # 01-15-2024
            "%d/%m/%Y",           # 15/01/2024
            "%d-%m-%Y",           # 15-01-2024
            "%Y/%m/%d",           # 2024/01/15
            "%B %d, %Y",          # January 15, 2024
            "%b %d, %Y",          # Jan 15, 2024
            "%d %B %Y",           # 15 January 2024
            "%d %b %Y",           # 15 Jan 2024
            "%Y%m%d",             # 20240115
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None


def extract_trades_from_pdf(pdf_bytes: bytes) -> Dict:
    """
    Convenience function to extract trades from PDF.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Dict with trades, total_pages, notes, and errors
    """
    extractor = PDFTradeExtractor()
    return extractor.extract_trades_from_pdf(pdf_bytes)
