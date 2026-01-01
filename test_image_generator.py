"""
Test script for Playwright-based image generator.

Generates a sample portfolio share image and saves it to screenshots/playwright-test.png
"""

import os
import sys

# Add app to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.services.image_generator import generate_share_image


def test_generate_image():
    """Test image generation with sample data."""
    # Create Flask app context for render_template
    app = create_app()

    with app.app_context():
        # Sample data similar to what the API would provide
        share_data = {
            'portfolio_return_pct': 23.45,
            'spy_return_pct': 15.20,
            'best_benchmark_ticker': 'NVDA',
            'best_benchmark_return_pct': 45.67,
            'worst_benchmark_ticker': 'AAPL',
            'worst_benchmark_return_pct': 8.90,
            'opportunity_cost_pct': -22.22
        }

        print("Generating share image with Playwright...")
        print(f"Sample data: {share_data}")

        # Generate image
        image_bytes = generate_share_image(share_data)

        # Save to screenshots directory
        screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)

        output_path = os.path.join(screenshots_dir, 'playwright-test.png')
        with open(output_path, 'wb') as f:
            f.write(image_bytes)

        print(f"Image saved to: {output_path}")
        print(f"Image size: {len(image_bytes)} bytes")
        print("Test completed successfully!")


if __name__ == '__main__':
    test_generate_image()
