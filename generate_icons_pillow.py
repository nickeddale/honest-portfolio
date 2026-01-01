#!/usr/bin/env python3
"""Generate PNG icons and favicon from SVG - using Pillow approach."""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

def create_icon(size):
    """Create an icon with HP text matching the SVG design."""
    # Create a new image with blue background
    img = Image.new('RGB', (size, size), color='#1e40af')
    draw = ImageDraw.Draw(img)

    # Calculate font size relative to image size
    # The SVG has font-size 280 for 512x512 image
    font_size = int(size * 280 / 512)

    # Try to use a bold font
    try:
        # Try to find Arial Bold or similar
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
        except:
            # Fallback to default font with size
            font = ImageFont.load_default()

    # Draw "HP" text centered
    text = "HP"

    # Get text bounding box to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Position text centered (matching SVG: x="256" y="340" for 512x512)
    # y="340" means the baseline is at 340, which is roughly 66% down
    x = (size - text_width) / 2
    y = size * 0.66 - text_height

    # Draw white text
    draw.text((x, y), text, fill='white', font=font)

    return img

def generate_png_icons():
    """Generate PNG icons."""
    print("Generating PNG icons...")

    # Create 192x192 icon
    print("Creating 192x192 icon...")
    icon_192 = create_icon(192)
    icon_192.save('app/static/icons/icon-192.png', 'PNG')
    print("✓ Created app/static/icons/icon-192.png")

    # Create 512x512 icon
    print("Creating 512x512 icon...")
    icon_512 = create_icon(512)
    icon_512.save('app/static/icons/icon-512.png', 'PNG')
    print("✓ Created app/static/icons/icon-512.png")

    return True

def generate_favicon():
    """Generate favicon.ico with multiple sizes."""
    print("Generating favicon.ico...")

    # Generate different sizes
    sizes = [16, 32, 48]
    images = []

    for size in sizes:
        print(f"  - Creating {size}x{size} favicon layer...")
        img = create_icon(size)
        images.append(img)

    # Save as ICO with multiple sizes
    images[0].save(
        'app/static/favicon.ico',
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )

    print("✓ Created app/static/favicon.ico")
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
            print(f"✓ {file_path} ({size:,} bytes)")
        else:
            print(f"✗ {file_path} - NOT FOUND!")
            all_exist = False

    return all_exist

def main():
    """Main function to generate all icons."""
    print("Icon Generator for Honest Portfolio")
    print("=" * 50)

    # Check if output directories exist
    os.makedirs('app/static/icons', exist_ok=True)

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
