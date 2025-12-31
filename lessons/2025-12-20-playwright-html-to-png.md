# Lessons Learned: Replace PIL with Playwright for Image Generation

**Date:** 2025-12-20
**Related Ticket:** HP-20
**Commit:** 496729e

## Problem Summary
The PIL-based image generator for share cards had significant issues:
- Font rendering problems (missing glyphs, Unicode characters showing as boxes)
- Inconsistent typography compared to the web preview
- Complex, hard-to-maintain code (700+ lines of drawing primitives)
- Two separate rendering systems (HTML for preview, PIL for download) that easily got out of sync

## Approach Taken
Replaced the entire PIL-based image generator with a Playwright-based HTML-to-PNG approach:
1. Created a Jinja2 HTML template with Tailwind CSS (`templates/share_image.html`)
2. Used Playwright to render the HTML and take a screenshot
3. Reduced code from 700+ lines to ~40 lines

Key decision: Use the same HTML/CSS styling for both the modal preview and the downloadable PNG, ensuring visual consistency.

## Key Lessons
- **Single source of truth for rendering**: When you have both a preview and a downloadable asset, use the same rendering technology for both. Maintaining two separate systems (HTML + PIL) leads to drift and inconsistency.
- **Browser rendering > custom drawing**: Modern browsers handle fonts, CSS, gradients, and layout far better than manual drawing code. Leverage that instead of reinventing it.
- **Playwright for server-side rendering**: Playwright works well for generating images server-side. The `page.screenshot()` API is simple and produces high-quality output.
- **Tailwind CDN in templates**: For standalone HTML templates rendered by Playwright, including the Tailwind CDN script works fine since Playwright loads it before screenshot.
- **Fixed viewport for social images**: Setting `viewport={'width': 1080, 'height': 1080}` ensures consistent 1:1 square output for social media.

## Potential Improvements
- **Browser pooling**: Currently each image generation launches a new browser. For high traffic, consider keeping a browser pool to reduce latency.
- **Template caching**: The HTML template could be pre-compiled for faster rendering.
- **Fallback**: If Playwright fails to install on a server, could fall back to a simpler solution or error gracefully.
