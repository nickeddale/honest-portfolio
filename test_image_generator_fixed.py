#!/usr/bin/env python3
"""Test script to regenerate portfolio summary images with fixes."""

import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.image_generator import SummaryCardGenerator


def main():
    """Generate test images with fixed arrow symbols and spacing."""
    generator = SummaryCardGenerator()

    # Ensure screenshots directory exists
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    # Test case 1: Underperformed (negative comparison)
    print("Generating test image 1: Underperformed scenario...")
    test_data_1 = {
        'portfolio_return_pct': 1.06,
        'spy_return_pct': 2.71,
        'best_benchmark_ticker': 'NVDA',
        'best_benchmark_return_pct': 4.21,
        'worst_benchmark_ticker': 'AAPL',
        'worst_benchmark_return_pct': 0.45,
        'opportunity_cost_pct': -3.15
    }

    image_bytes_1 = generator.generate(test_data_1)
    output_path_1 = screenshots_dir / "share-redesign-test.png"

    with open(output_path_1, 'wb') as f:
        f.write(image_bytes_1)

    print(f"✓ Saved: {output_path_1.absolute()}")
    print(f"  Portfolio: +1.06%, SPY: +2.71%")
    print(f"  Comparison: Underperformed by 1.65%")

    # Test case 2: Outperformed (positive comparison)
    print("\nGenerating test image 2: Outperformed scenario...")
    test_data_2 = {
        'portfolio_return_pct': 3.45,
        'spy_return_pct': 2.71,
        'best_benchmark_ticker': 'NVDA',
        'best_benchmark_return_pct': 4.21,
        'worst_benchmark_ticker': 'AAPL',
        'worst_benchmark_return_pct': 0.45,
        'opportunity_cost_pct': -0.76
    }

    image_bytes_2 = generator.generate(test_data_2)
    output_path_2 = screenshots_dir / "share-redesign-test-beat-spy.png"

    with open(output_path_2, 'wb') as f:
        f.write(image_bytes_2)

    print(f"✓ Saved: {output_path_2.absolute()}")
    print(f"  Portfolio: +3.45%, SPY: +2.71%")
    print(f"  Comparison: Outperformed by 0.74%")

    print("\n" + "="*60)
    print("FIXES APPLIED:")
    print("="*60)
    print("1. Removed Unicode arrows (▲/▼) - replaced with plain text")
    print("2. Increased percentage spacing (140 → 200 pixels from center)")
    print("="*60)


if __name__ == '__main__':
    main()
