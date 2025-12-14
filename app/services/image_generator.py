"""
Portfolio summary card image generator.

Generates shareable PNG images for social media with portfolio performance data.
Uses neobrutalism design with gradient backgrounds and bold typography.
Square format (1:1 ratio, 1080x1080) optimized for social media sharing.
"""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Tuple


class SummaryCardGenerator:
    """Generates portfolio summary cards as PNG images with neobrutalism styling."""

    # Square dimensions (1:1 ratio for social media)
    WIDTH = 1080
    HEIGHT = 1080

    # Neobrutalism design system colors
    PRIMARY_BLUE = "#3b82f6"
    PURPLE = "#9333ea"
    DARK_BORDER = "#1c1917"
    SUCCESS_GREEN = "#22c55e"
    DESTRUCTIVE_RED = "#ef4444"
    CARD_BG = "#ffffff"
    TEXT_WHITE = "#ffffff"
    TEXT_GRAY = "#6b7280"
    TEXT_LIGHT_BLUE = "#dbeafe"

    # Gradient colors (Blue to Purple, top to bottom)
    GRADIENT_START = (59, 130, 246)  # Blue #3b82f6
    GRADIENT_END = (147, 51, 234)    # Purple #9333ea

    # Layout constants
    TOP_PADDING = 80
    BOTTOM_PADDING = 80
    SIDE_PADDING = 60
    CARD_PADDING = 30
    BORDER_WIDTH = 3
    CORNER_RADIUS = 8
    SECTION_GAP = 40

    def __init__(self):
        """Initialize the generator."""
        self._setup_fonts()

    def _setup_fonts(self):
        """Setup fonts with fallbacks to system defaults."""
        # Try to use bold system fonts for neobrutalism style
        try:
            # Try common bold font locations for macOS
            self.font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 56)
            self.font_hero = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
            self.font_ticker = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            self.font_return = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            self.font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            self.font_footer = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except OSError:
            try:
                # Try Arial Bold as fallback
                self.font_title = ImageFont.truetype("arialbd.ttf", 56)
                self.font_hero = ImageFont.truetype("arialbd.ttf", 80)
                self.font_ticker = ImageFont.truetype("arialbd.ttf", 48)
                self.font_return = ImageFont.truetype("arialbd.ttf", 36)
                self.font_label = ImageFont.truetype("arialbd.ttf", 24)
                self.font_footer = ImageFont.truetype("arialbd.ttf", 20)
            except OSError:
                # Last resort: default font
                self.font_title = ImageFont.load_default()
                self.font_hero = ImageFont.load_default()
                self.font_ticker = ImageFont.load_default()
                self.font_return = ImageFont.load_default()
                self.font_label = ImageFont.load_default()
                self.font_footer = ImageFont.load_default()

    def _create_gradient_background(self) -> Image.Image:
        """Create a blue-to-purple gradient background (top to bottom)."""
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT))
        draw = ImageDraw.Draw(img)

        # Create vertical gradient from top to bottom
        for y in range(self.HEIGHT):
            # Calculate position in gradient (0.0 to 1.0)
            ratio = y / self.HEIGHT

            # Interpolate between start and end colors
            r = int(self.GRADIENT_START[0] + (self.GRADIENT_END[0] - self.GRADIENT_START[0]) * ratio)
            g = int(self.GRADIENT_START[1] + (self.GRADIENT_END[1] - self.GRADIENT_START[1]) * ratio)
            b = int(self.GRADIENT_START[2] + (self.GRADIENT_END[2] - self.GRADIENT_START[2]) * ratio)

            draw.line([(0, y), (self.WIDTH, y)], fill=(r, g, b))

        return img

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        xy: Tuple[int, int, int, int],
        radius: int,
        fill: str = None,
        outline: str = None,
        width: int = 1
    ):
        """Draw a rounded rectangle with border."""
        x1, y1, x2, y2 = xy

        # Draw the filled rounded rectangle
        if fill:
            draw.rounded_rectangle(xy, radius=radius, fill=fill)

        # Draw the border
        if outline:
            draw.rounded_rectangle(xy, radius=radius, outline=outline, width=width)

    def _draw_card(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int
    ):
        """Draw a neobrutalism card with white background and dark border."""
        self._draw_rounded_rectangle(
            draw,
            (x, y, x + width, y + height),
            radius=self.CORNER_RADIUS,
            fill=self.CARD_BG,
            outline=self.DARK_BORDER,
            width=self.BORDER_WIDTH
        )

    def _format_percentage(self, value: float) -> str:
        """Format percentage with sign."""
        if value >= 0:
            return f"+{value:.2f}%"
        return f"{value:.2f}%"

    def _get_color_for_value(self, value: float) -> str:
        """Get color based on positive/negative value."""
        return self.SUCCESS_GREEN if value >= 0 else self.DESTRUCTIVE_RED

    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        font: ImageFont.FreeTypeFont,
        color: str,
        align: str = 'left'
    ) -> Tuple[int, int]:
        """
        Draw text and return dimensions.

        Args:
            align: 'left', 'center', or 'right'

        Returns:
            Tuple of (width, height) of the drawn text
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if align == 'center':
            x = x - text_width // 2
        elif align == 'right':
            x = x - text_width

        draw.text((x, y), text, fill=color, font=font)
        return (text_width, text_height)

    def _draw_title(
        self,
        draw: ImageDraw.ImageDraw,
        y_start: int
    ) -> int:
        """
        Draw the title section.

        Returns:
            Y position after this section
        """
        center_x = self.WIDTH // 2

        # Title: "My Portfolio Performance"
        self._draw_text(
            draw,
            "My Portfolio Performance",
            center_x,
            y_start,
            self.font_title,
            self.TEXT_WHITE,
            align='center'
        )

        return y_start + 80

    def _draw_your_return_card(
        self,
        draw: ImageDraw.ImageDraw,
        portfolio_return: float,
        y_start: int
    ) -> int:
        """
        Draw the main "Your Return" card.

        Returns:
            Y position after this section
        """
        card_width = self.WIDTH - 2 * self.SIDE_PADDING
        card_height = 180
        card_x = self.SIDE_PADDING
        card_y = y_start

        # Draw card background
        self._draw_card(draw, card_x, card_y, card_width, card_height)

        center_x = self.WIDTH // 2

        # Label: "Your Return"
        label_y = card_y + self.CARD_PADDING
        self._draw_text(
            draw,
            "Your Return",
            center_x,
            label_y,
            self.font_label,
            self.TEXT_GRAY,
            align='center'
        )

        # Return percentage (hero number)
        return_text = self._format_percentage(portfolio_return)
        return_color = self._get_color_for_value(portfolio_return)
        return_y = label_y + 55

        self._draw_text(
            draw,
            return_text,
            center_x,
            return_y,
            self.font_hero,
            return_color,
            align='center'
        )

        return card_y + card_height

    def _draw_spy_return_card(
        self,
        draw: ImageDraw.ImageDraw,
        spy_return: float,
        y_start: int
    ) -> int:
        """
        Draw the S&P 500 return card.

        Returns:
            Y position after this section
        """
        card_width = self.WIDTH - 2 * self.SIDE_PADDING
        card_height = 140
        card_x = self.SIDE_PADDING
        card_y = y_start

        # Draw card background
        self._draw_card(draw, card_x, card_y, card_width, card_height)

        center_x = self.WIDTH // 2

        # Label: "S&P 500 Return"
        label_y = card_y + self.CARD_PADDING
        self._draw_text(
            draw,
            "S&P 500 Return",
            center_x,
            label_y,
            self.font_label,
            self.TEXT_GRAY,
            align='center'
        )

        # Ticker and Return on same line
        ticker_y = label_y + 50

        # Draw "SPY" on the left side of center
        self._draw_text(
            draw,
            "SPY",
            center_x - 80,
            ticker_y,
            self.font_ticker,
            self.DARK_BORDER,
            align='center'
        )

        # Draw return percentage on the right side of center
        return_text = self._format_percentage(spy_return)
        return_color = self._get_color_for_value(spy_return)
        self._draw_text(
            draw,
            return_text,
            center_x + 80,
            ticker_y,
            self.font_return,
            return_color,
            align='center'
        )

        return card_y + card_height

    def _draw_benchmark_cards(
        self,
        draw: ImageDraw.ImageDraw,
        best_ticker: str,
        best_return: float,
        worst_ticker: str,
        worst_return: float,
        y_start: int
    ) -> int:
        """
        Draw two-column benchmark cards (Best and Worst).

        Returns:
            Y position after this section
        """
        card_height = 160
        gap = 24
        card_width = (self.WIDTH - 2 * self.SIDE_PADDING - gap) // 2

        # Left card (Best Benchmark)
        left_x = self.SIDE_PADDING
        self._draw_card(draw, left_x, y_start, card_width, card_height)

        # Label
        label_y = y_start + self.CARD_PADDING
        self._draw_text(
            draw,
            "Best Benchmark",
            left_x + card_width // 2,
            label_y,
            self.font_label,
            self.TEXT_GRAY,
            align='center'
        )

        # Ticker
        ticker_y = label_y + 45
        self._draw_text(
            draw,
            best_ticker,
            left_x + card_width // 2,
            ticker_y,
            self.font_ticker,
            self.DARK_BORDER,
            align='center'
        )

        # Return
        return_y = ticker_y + 70
        best_return_text = self._format_percentage(best_return)
        best_color = self._get_color_for_value(best_return)
        self._draw_text(
            draw,
            best_return_text,
            left_x + card_width // 2,
            return_y,
            self.font_return,
            best_color,
            align='center'
        )

        # Right card (Worst Benchmark)
        right_x = left_x + card_width + gap
        self._draw_card(draw, right_x, y_start, card_width, card_height)

        # Label
        self._draw_text(
            draw,
            "Worst Benchmark",
            right_x + card_width // 2,
            label_y,
            self.font_label,
            self.TEXT_GRAY,
            align='center'
        )

        # Ticker
        self._draw_text(
            draw,
            worst_ticker,
            right_x + card_width // 2,
            ticker_y,
            self.font_ticker,
            self.DARK_BORDER,
            align='center'
        )

        # Return
        worst_return_text = self._format_percentage(worst_return)
        worst_color = self._get_color_for_value(worst_return)
        self._draw_text(
            draw,
            worst_return_text,
            right_x + card_width // 2,
            return_y,
            self.font_return,
            worst_color,
            align='center'
        )

        return y_start + card_height

    def _draw_opportunity_cost_card(
        self,
        draw: ImageDraw.ImageDraw,
        opportunity_cost: float,
        best_ticker: str,
        y_start: int
    ) -> int:
        """
        Draw opportunity cost card.

        Returns:
            Y position after this section
        """
        card_width = self.WIDTH - 2 * self.SIDE_PADDING
        card_height = 160
        card_x = self.SIDE_PADDING

        # Draw card
        self._draw_card(draw, card_x, y_start, card_width, card_height)

        center_x = self.WIDTH // 2

        # Label
        label_y = y_start + self.CARD_PADDING
        self._draw_text(
            draw,
            "Opportunity Cost",
            center_x,
            label_y,
            self.font_label,
            self.TEXT_GRAY,
            align='center'
        )

        # Opportunity cost value
        opp_text = self._format_percentage(opportunity_cost)
        opp_color = self._get_color_for_value(opportunity_cost)
        opp_y = label_y + 50

        self._draw_text(
            draw,
            opp_text,
            center_x,
            opp_y,
            self.font_hero,
            opp_color,
            align='center'
        )

        # vs ticker
        vs_text = f"vs {best_ticker}"
        vs_y = opp_y + 70
        self._draw_text(
            draw,
            vs_text,
            center_x,
            vs_y,
            self.font_footer,
            self.TEXT_GRAY,
            align='center'
        )

        return y_start + card_height

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        y_start: int
    ) -> int:
        """
        Draw footer text.

        Returns:
            Y position after this section
        """
        center_x = self.WIDTH // 2

        footer_text = "Track your portfolio at Honest Portfolio"
        self._draw_text(
            draw,
            footer_text,
            center_x,
            y_start,
            self.font_footer,
            self.TEXT_LIGHT_BLUE,
            align='center'
        )

        return y_start + 30

    def generate(self, share_data: Dict) -> bytes:
        """
        Generate PNG image bytes from share data.

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
        # Create gradient background
        img = self._create_gradient_background()
        draw = ImageDraw.Draw(img)

        # Extract data
        portfolio_return = share_data.get('portfolio_return_pct', 0)
        spy_return = share_data.get('spy_return_pct')  # May be None for old shares
        best_ticker = share_data.get('best_benchmark_ticker', 'N/A')
        best_return = share_data.get('best_benchmark_return_pct', 0)
        worst_ticker = share_data.get('worst_benchmark_ticker', 'N/A')
        worst_return = share_data.get('worst_benchmark_return_pct', 0)
        opportunity_cost = share_data.get('opportunity_cost_pct', 0)

        # Layout from top to bottom with adjusted spacing
        y = self.TOP_PADDING

        # Title
        y = self._draw_title(draw, y)

        # Your Return card
        y = self._draw_your_return_card(draw, portfolio_return, y)

        # SPY Return card (if available)
        if spy_return is not None:
            y += 30
            y = self._draw_spy_return_card(draw, spy_return, y)

        # Benchmark cards (side by side)
        y += 30
        y = self._draw_benchmark_cards(
            draw,
            best_ticker,
            best_return,
            worst_ticker,
            worst_return,
            y
        )

        # Opportunity cost card
        y += 30
        y = self._draw_opportunity_cost_card(draw, opportunity_cost, best_ticker, y)

        # Footer
        y += 30
        y = self._draw_footer(draw, y)

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()


def generate_share_image(share_data: Dict) -> bytes:
    """
    Convenience function to generate share image.

    Args:
        share_data: Dictionary containing portfolio performance data

    Returns:
        PNG image as bytes
    """
    generator = SummaryCardGenerator()
    return generator.generate(share_data)
