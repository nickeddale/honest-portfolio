# PWA Icons

This directory should contain the following icon files:

- **icon-192.png** - 192x192 pixel PNG icon
- **icon-512.png** - 512x512 pixel PNG icon

## Creating the Icons

You can create these icons using:

1. **Online Tools**:
   - https://www.favicon-generator.org/
   - https://realfavicongenerator.net/

2. **Design Software**:
   - Create a simple design with "HP" or a chart/portfolio symbol
   - Export as PNG at 192x192 and 512x512 sizes

3. **Quick SVG to PNG Conversion**:
   - Use ImageMagick: `convert icon.svg -resize 192x192 icon-192.png`
   - Use ImageMagick: `convert icon.svg -resize 512x512 icon-512.png`

## Placeholder Icon

For now, you can use a solid color square or generate a simple icon with your initials/logo.

The app will work without these icons, but the PWA install prompt may not appear and the app icon won't display properly when installed.
