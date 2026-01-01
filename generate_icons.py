#!/usr/bin/env python3
"""Generate PNG icons and favicon from SVG source."""

import os
import sys

try:
    import cairosvg
    from PIL import Image
    import io
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cairosvg", "Pillow"])
    print("Packages installed. Please run the script again.")
    sys.exit(1)

def generate_png_icons():
    """Generate PNG icons from SVG source."""
    svg_path = 'app/static/icons/icon.svg'

    if not os.path.exists(svg_path):
        print(f"Error: {svg_path} not found!")
        return False

    print(f"Reading SVG from: {svg_path}")

    # Generate 192x192 icon
    print("Generating 192x192 icon...")
    cairosvg.svg2png(
        url=svg_path,
        write_to='app/static/icons/icon-192.png',
        output_width=192,
        output_height=192
    )
    print("✓ Created app/static/icons/icon-192.png")

    # Generate 512x512 icon
    print("Generating 512x512 icon...")
    cairosvg.svg2png(
        url=svg_path,
        write_to='app/static/icons/icon-512.png',
        output_width=512,
        output_height=512
    )
    print("✓ Created app/static/icons/icon-512.png")

    return True

def generate_favicon():
    """Generate favicon.ico with multiple sizes."""
    svg_path = 'app/static/icons/icon.svg'
    favicon_path = 'app/static/favicon.ico'

    print("Generating favicon.ico...")

    # Generate different sizes
    sizes = [16, 32, 48]
    images = []

    for size in sizes:
        print(f"  - Creating {size}x{size} favicon layer...")
        png_data = cairosvg.svg2png(
            url=svg_path,
            output_width=size,
            output_height=size
        )
        img = Image.open(io.BytesIO(png_data))
        images.append(img)

    # Save as ICO with multiple sizes
    images[0].save(
        favicon_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )

    print(f"✓ Created {favicon_path}")
    return True

def verify_files():
    """Verify that all generated files exist."""
    files = [
        'app/static/icons/icon-192.png',
        'app/static/icons/icon-512.png',
        'app/static/favicon.ico'
    ]

    print("\nVerifying generated files...")
    all_exist = True
    for file_path in files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✓ {file_path} ({size} bytes)")
        else:
            print(f"✗ {file_path} - NOT FOUND!")
            all_exist = False

    return all_exist

def main():
    """Main function to generate all icons."""
    print("Icon Generator for Honest Portfolio")
    print("=" * 50)

    # Generate PNG icons
    if not generate_png_icons():
        print("\nFailed to generate PNG icons!")
        return 1

    # Generate favicon
    if not generate_favicon():
        print("\nFailed to generate favicon!")
        return 1

    # Verify all files
    if not verify_files():
        print("\nWarning: Some files were not created successfully!")
        return 1

    print("\n" + "=" * 50)
    print("All icons generated successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
