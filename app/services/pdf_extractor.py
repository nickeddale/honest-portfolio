"""
PDF trade extraction service using Mistral OCR + OpenAI ChatGPT.
"""

import base64
import json
import io
from datetime import datetime
from typing import Dict, List, Optional
import fitz  # PyMuPDF
from openai import OpenAI
from mistralai import Mistral
from flask import current_app


class PDFTradeExtractor:
    """Extracts trade data from PDF documents using Mistral OCR + ChatGPT."""

    EXTRACTION_PROMPT = """You are a financial document analyzer specializing in brokerage statements and trade confirmations.

Extract all stock BUY transactions from this document.

IMPORTANT CONTEXT:
- This text was extracted from a PDF using OCR (Optical Character Recognition)
- Tables are formatted in markdown
- The text may contain headers, footers, page numbers, and OCR artifacts
- Some formatting may be imperfect due to OCR processing

For each BUY trade, extract:
- ticker: The standard stock ticker symbol (e.g., AAPL, TSLA, MSFT)
  IMPORTANT: If the document shows a company name instead of ticker, convert it:
  - "Apple Inc." or "APPLE INC" → AAPL
  - "Microsoft Corporation" or "MICROSOFT CORP" → MSFT
  - "NVIDIA Corporation" or "NVIDIA CORP" → NVDA
  - "Tesla Inc." or "TESLA INC" → TSLA
  - "Amazon.com Inc." or "AMAZON COM INC" → AMZN
  - "Alphabet Inc." or "GOOGLE" → GOOGL
  - "Meta Platforms" or "META PLATFORMS INC" → META
  - "Berkshire Hathaway" → BRK.B
  - "JPMorgan Chase" → JPM
  - "Johnson & Johnson" → JNJ
  For other companies, use your knowledge to provide the correct NYSE/NASDAQ ticker.

- purchase_date: Date of the trade in YYYY-MM-DD format
- quantity: Number of shares bought (can be fractional, e.g., 0.5 shares)
- price_per_share: Price per share in USD (exclude fees/commissions)
- total_amount: Total transaction amount in USD (optional, exclude fees)

Rules:
- Only extract BUY transactions (not sells, dividends, or transfers)
- Be precise with numbers - do not round
- If a ticker symbol is already shown (like "AAPL"), use it directly
- Ignore mutual funds, ETFs with non-standard symbols unless clearly identifiable
- Look for transaction tables, trade confirmations, or account activity sections
- Be tolerant of OCR errors in company names but strict with numerical accuracy
- If you see duplicate entries, include all (deduplication happens later)

Return a JSON object with a "trades" array. If no trades found, return {"trades": []}.

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
    "notes": "Extracted from Fidelity monthly statement"
}"""

    def __init__(self):
        self.openai_client = None
        self.mistral_client = None

    def _get_openai_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self.openai_client is None:
            api_key = current_app.config.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            self.openai_client = OpenAI(api_key=api_key)
        return self.openai_client

    def _get_mistral_client(self) -> Mistral:
        """Lazy initialization of Mistral client."""
        if self.mistral_client is None:
            api_key = current_app.config.get('MISTRAL_API_KEY')
            if not api_key:
                raise ValueError("MISTRAL_API_KEY not configured")
            self.mistral_client = Mistral(api_key=api_key)
        return self.mistral_client

    def pdf_to_markdown(self, pdf_bytes: bytes) -> dict:
        """
        Convert PDF to markdown using Mistral OCR API.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Dict with:
                - markdown: Extracted markdown text
                - pages: Number of pages processed
                - metadata: Optional OCR metadata
        """
        try:
            client = self._get_mistral_client()

            # Encode PDF to base64 data URI
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            data_uri = f"data:application/pdf;base64,{base64_pdf}"

            # Call Mistral OCR API with base64-encoded PDF
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": data_uri
                },
                table_format="markdown",
                include_image_base64=False
            )

            # Extract markdown (adjust field names based on actual API response)
            markdown_text = getattr(ocr_response, 'text', '') or \
                           getattr(ocr_response, 'content', '') or \
                           str(ocr_response)

            if not markdown_text or markdown_text.strip() == "":
                raise ValueError("OCR returned empty text. PDF may be corrupted or image-only.")

            page_count = getattr(ocr_response, 'page_count', 1)

            current_app.logger.info(f"OCR extracted {len(markdown_text)} chars from {page_count} pages")

            return {
                "markdown": markdown_text,
                "pages": page_count,
                "metadata": getattr(ocr_response, 'metadata', None)
            }

        except Exception as e:
            if "rate limit" in str(e).lower():
                raise ValueError("OCR service temporarily unavailable. Please try again in a few minutes.")
            elif "quota" in str(e).lower():
                raise ValueError("OCR service quota exceeded. Please contact support.")
            raise ValueError(f"Failed to perform OCR on PDF: {str(e)}")

    def extract_trades_from_markdown(self, markdown_text: str) -> Dict:
        """
        Extract trades from markdown text using ChatGPT.

        Args:
            markdown_text: OCR-extracted markdown content

        Returns:
            Dict with 'trades' array and optional 'notes'
        """
        try:
            client = self._get_openai_client()

            # Call OpenAI ChatGPT with text-only input
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": f"{self.EXTRACTION_PROMPT}\n\n--- DOCUMENT TEXT ---\n{markdown_text}"
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=2000
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            if "trades" not in result:
                result["trades"] = []

            return result

        except json.JSONDecodeError as e:
            current_app.logger.error(f"ChatGPT returned invalid JSON: {content}")
            raise ValueError(f"Failed to parse extraction results. Document format may not be supported.")
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise ValueError("Trade extraction service temporarily busy. Try again in a few minutes.")
            raise ValueError(f"Failed to extract trades from markdown: {str(e)}")

    def extract_trades_from_pdf(self, pdf_bytes: bytes) -> Dict:
        """
        Extract all trades from a PDF using Mistral OCR + ChatGPT.

        Returns:
            Dict with trades, total_pages, notes, and errors
        """
        all_notes = []
        errors = []

        try:
            # Step 1: Convert PDF to markdown using Mistral OCR
            current_app.logger.info("Starting Mistral OCR extraction")
            ocr_result = self.pdf_to_markdown(pdf_bytes)
            markdown_text = ocr_result["markdown"]
            total_pages = ocr_result["pages"]

            # Step 2: Extract trades from markdown using ChatGPT
            current_app.logger.info("Starting ChatGPT trade extraction")
            extraction_result = self.extract_trades_from_markdown(markdown_text)

            all_trades = extraction_result.get("trades", [])
            if "notes" in extraction_result:
                all_notes.append(extraction_result["notes"])

            current_app.logger.info(f"Extracted {len(all_trades)} raw trades")

            # Deduplicate and validate (existing methods)
            unique_trades = self._deduplicate_trades(all_trades)
            current_app.logger.info(f"After deduplication: {len(unique_trades)} unique trades")

            validated_trades = self._validate_trades(unique_trades)
            current_app.logger.info(f"After validation: {len(validated_trades)} valid trades")

            return {
                "trades": validated_trades,
                "total_pages": total_pages,
                "notes": all_notes,
                "errors": errors if errors else None
            }

        except ValueError as e:
            error_msg = str(e)
            current_app.logger.error(f"PDF extraction failed: {error_msg}")
            errors.append(error_msg)

            return {
                "trades": [],
                "total_pages": 0,
                "notes": all_notes,
                "errors": errors
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error in PDF extraction: {e}")
            errors.append(f"Unexpected error: {str(e)}")

            return {
                "trades": [],
                "total_pages": 0,
                "notes": all_notes,
                "errors": errors
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
