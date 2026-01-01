"""
Test script for generating sample share images.

Creates sample share images using the image_generator to verify the design
and layout with realistic data.
"""

import os
from app.services.image_generator import generate_share_image


def test_underperformed_spy():
    """Test case: Portfolio underperformed S&P 500."""
    print("Generating test image: Portfolio underperformed S&P 500...")

    share_data = {
        'portfolio_return_pct': 1.06,
        'spy_return_pct': 2.71,
        'best_benchmark_ticker': 'META',
        'best_benchmark_return_pct': 13.14,
        'worst_benchmark_ticker': 'NVDA',
        'worst_benchmark_return_pct': -3.17,
        'opportunity_cost_pct': -12.08
    }

    try:
        # Generate the image
        image_bytes = generate_share_image(share_data)

        # Ensure screenshots directory exists
        os.makedirs('screenshots', exist_ok=True)

        # Save to file
        output_path = 'screenshots/share-redesign-test.png'
        with open(output_path, 'wb') as f:
            f.write(image_bytes)

        print(f"✓ Successfully generated: {output_path}")
        print(f"  - Portfolio return: {share_data['portfolio_return_pct']:.2f}%")
        print(f"  - S&P 500 return: {share_data['spy_return_pct']:.2f}%")
        print(f"  - Best benchmark: {share_data['best_benchmark_ticker']} ({share_data['best_benchmark_return_pct']:.2f}%)")
        print(f"  - Worst benchmark: {share_data['worst_benchmark_ticker']} ({share_data['worst_benchmark_return_pct']:.2f}%)")
        print(f"  - Opportunity cost: {share_data['opportunity_cost_pct']:.2f}%")
        return True
    except Exception as e:
        print(f"✗ Error generating image: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_beat_spy():
    """Test case: Portfolio beat S&P 500 but not the best benchmark."""
    print("\nGenerating test image: Portfolio beat S&P 500...")

    share_data = {
        'portfolio_return_pct': 5.50,
        'spy_return_pct': 2.71,
        'best_benchmark_ticker': 'AAPL',
        'best_benchmark_return_pct': 8.25,
        'worst_benchmark_ticker': 'AMZN',
        'worst_benchmark_return_pct': 1.20,
        'opportunity_cost_pct': -2.75
    }

    try:
        # Generate the image
        image_bytes = generate_share_image(share_data)

        # Ensure screenshots directory exists
        os.makedirs('screenshots', exist_ok=True)

        # Save to file
        output_path = 'screenshots/share-redesign-test-beat-spy.png'
        with open(output_path, 'wb') as f:
            f.write(image_bytes)

        print(f"✓ Successfully generated: {output_path}")
        print(f"  - Portfolio return: {share_data['portfolio_return_pct']:.2f}%")
        print(f"  - S&P 500 return: {share_data['spy_return_pct']:.2f}%")
        print(f"  - Best benchmark: {share_data['best_benchmark_ticker']} ({share_data['best_benchmark_return_pct']:.2f}%)")
        print(f"  - Worst benchmark: {share_data['worst_benchmark_ticker']} ({share_data['worst_benchmark_return_pct']:.2f}%)")
        print(f"  - Opportunity cost: {share_data['opportunity_cost_pct']:.2f}%")
        return True
    except Exception as e:
        print(f"✗ Error generating image: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("Share Image Generator Test Suite")
    print("=" * 70)

    results = []

    # Test 1: Underperformed S&P 500
    results.append(("Underperformed S&P 500", test_underperformed_spy()))

    # Test 2: Beat S&P 500
    results.append(("Beat S&P 500", test_beat_spy()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        exit(1)
