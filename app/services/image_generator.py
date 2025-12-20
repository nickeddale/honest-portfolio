"""
Portfolio summary card image generator using Playwright.

Renders HTML template to PNG for shareable social media images.
"""

from typing import Dict
from flask import render_template
from playwright.sync_api import sync_playwright


def generate_share_image(share_data: Dict) -> bytes:
    """
    Generate PNG image from share data using Playwright.

    Args:
        share_data: Dictionary containing:
            - portfolio_return_pct: float
            - spy_return_pct: float (optional)
            - best_benchmark_ticker: str
            - best_benchmark_return_pct: float
            - worst_benchmark_ticker: str
            - worst_benchmark_return_pct: float
            - opportunity_cost_pct: float

    Returns:
        PNG image as bytes
    """
    # Render HTML template with share data
    html = render_template('share_image.html', **share_data)

    # Use Playwright to render HTML to PNG
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1080, 'height': 1080})
        page.set_content(html, wait_until='networkidle')
        screenshot = page.screenshot(type='png')
        browser.close()

    return screenshot
