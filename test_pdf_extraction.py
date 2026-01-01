#!/usr/bin/env python3
"""
Test script for PDF extraction using Mistral OCR + ChatGPT.
"""

import sys
import json
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Create Flask app context
from app import create_app

app = create_app()

def test_extraction(pdf_path: str):
    """Test PDF extraction with a sample file."""
    print(f"\n{'='*80}")
    print(f"Testing PDF Extraction: {pdf_path}")
    print(f"{'='*80}\n")

    # Read PDF file
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    print(f"✓ PDF loaded: {len(pdf_bytes):,} bytes\n")

    # Import and run extraction
    with app.app_context():
        from app.services.pdf_extractor import PDFTradeExtractor

        extractor = PDFTradeExtractor()

        print("Step 1: Converting PDF to markdown using Mistral OCR...")
        try:
            ocr_result = extractor.pdf_to_markdown(pdf_bytes)
            print(f"✓ OCR completed!")
            print(f"  - Pages processed: {ocr_result['pages']}")
            print(f"  - Markdown length: {len(ocr_result['markdown']):,} characters")
            print(f"\nFirst 500 chars of markdown:")
            print("-" * 80)
            print(ocr_result['markdown'][:500])
            print("-" * 80)
        except Exception as e:
            print(f"✗ OCR failed: {e}")
            return

        print("\nStep 2: Extracting trades from markdown using ChatGPT...")
        try:
            extraction_result = extractor.extract_trades_from_markdown(ocr_result['markdown'])
            print(f"✓ Extraction completed!")
            print(f"  - Trades found: {len(extraction_result.get('trades', []))}")
            if extraction_result.get('notes'):
                print(f"  - Notes: {extraction_result['notes']}")
        except Exception as e:
            print(f"✗ Extraction failed: {e}")
            return

        print("\nStep 3: Running full pipeline (with validation)...")
        try:
            result = extractor.extract_trades_from_pdf(pdf_bytes)
            print(f"✓ Full pipeline completed!")
            print(f"\n{'='*80}")
            print("RESULTS:")
            print(f"{'='*80}")
            print(f"Total pages: {result['total_pages']}")
            print(f"Trades extracted: {len(result['trades'])}")
            print(f"Errors: {result.get('errors', 'None')}")

            if result['trades']:
                print(f"\nExtracted Trades:")
                print("-" * 80)
                for i, trade in enumerate(result['trades'], 1):
                    print(f"\n{i}. {trade['ticker']}")
                    print(f"   Date: {trade['purchase_date']}")
                    print(f"   Quantity: {trade['quantity']} shares")
                    print(f"   Price: ${trade['price_per_share']:.2f}")
                    print(f"   Total: ${trade['total_amount']:.2f}")
            else:
                print("\nNo trades were extracted.")
                if result.get('notes'):
                    print(f"Notes: {result['notes']}")

            print(f"\n{'='*80}")
            print("✓ Test completed successfully!")
            print(f"{'='*80}\n")

        except Exception as e:
            print(f"✗ Full pipeline failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    pdf_file = "Account statement.pdf"

    if not Path(pdf_file).exists():
        print(f"Error: PDF file not found: {pdf_file}")
        sys.exit(1)

    test_extraction(pdf_file)
