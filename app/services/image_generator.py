"""
Portfolio summary card image generator.

Generates shareable PNG images for social media with portfolio performance data.
"""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import Dict


class SummaryCardGenerator:
    """Generates portfolio summary cards as PNG images."""

    # Image dimensions (optimized for social media)
    WIDTH = 1200
    HEIGHT = 630

    # Colors
    BG_COLOR = "#ffffff"
    HEADER_COLOR = "#374151"
    LABEL_COLOR = "#6b7280"
    POSITIVE_COLOR = "#10b981"
    NEGATIVE_COLOR = "#ef4444"
    DIVIDER_COLOR = "#e5e7eb"

    # Padding and spacing
    PADDING = 60
    SECTION_SPACING = 50

    def __init__(self):
        """Initialize the generator."""
        self._setup_fonts()

    def _setup_fonts(self):
        """Setup fonts with fallbacks to system defaults."""
        # Try to use system fonts, fall back to PIL default
        try:
            # Try common font locations
            self.font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            self.font_header = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            self.font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
            self.font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            self.font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            self.font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        except OSError:
            # Fallback to default font with size parameter
            self.font_title = ImageFont.load_default()
            self.font_header = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_label = ImageFont.load_default()

    def _format_percentage(self, value: float) -> str:
        """Format percentage with sign."""
        if value >= 0:
            return f"+{value:.1f}%"
        return f"{value:.1f}%"

    def _get_color_for_value(self, value: float) -> str:
        """Get color based on positive/negative value."""
        return self.POSITIVE_COLOR if value >= 0 else self.NEGATIVE_COLOR

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        y: int,
        font: ImageFont.FreeTypeFont,
        color: str,
        max_width: int = None
    ):
        """Draw text centered horizontally."""
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        # Truncate if too wide
        if max_width and text_width > max_width:
            while text_width > max_width and len(text) > 0:
                text = text[:-1]
                bbox = draw.textbbox((0, 0), text + "...", font=font)
                text_width = bbox[2] - bbox[0]
            text = text + "..."

        x = (self.WIDTH - text_width) // 2
        draw.text((x, y), text, fill=color, font=font)

    def _draw_divider(self, draw: ImageDraw.ImageDraw, y: int):
        """Draw a horizontal divider line."""
        margin = self.PADDING * 2
        draw.line(
            [(margin, y), (self.WIDTH - margin, y)],
            fill=self.DIVIDER_COLOR,
            width=2
        )

    def _draw_benchmark_column(
        self,
        draw: ImageDraw.ImageDraw,
        label: str,
        ticker: str,
        return_pct: float,
        x_center: int,
        y: int
    ):
        """Draw a benchmark column (label, ticker, and return)."""
        # Label
        label_bbox = draw.textbbox((0, 0), label, font=self.font_label)
        label_width = label_bbox[2] - label_bbox[0]
        draw.text(
            (x_center - label_width // 2, y),
            label,
            fill=self.LABEL_COLOR,
            font=self.font_label
        )

        # Ticker and return
        y += 40
        ticker_return = f"{ticker}  {self._format_percentage(return_pct)}"
        color = self._get_color_for_value(return_pct)

        ticker_bbox = draw.textbbox((0, 0), ticker_return, font=self.font_medium)
        ticker_width = ticker_bbox[2] - ticker_bbox[0]

        # Ensure it fits within column width
        max_width = self.WIDTH // 2 - self.PADDING * 2
        if ticker_width > max_width:
            # Just show ticker on one line, return on next
            ticker_bbox = draw.textbbox((0, 0), ticker, font=self.font_medium)
            ticker_width = ticker_bbox[2] - ticker_bbox[0]
            draw.text(
                (x_center - ticker_width // 2, y),
                ticker,
                fill=color,
                font=self.font_medium
            )

            y += 55
            return_text = self._format_percentage(return_pct)
            return_bbox = draw.textbbox((0, 0), return_text, font=self.font_medium)
            return_width = return_bbox[2] - return_bbox[0]
            draw.text(
                (x_center - return_width // 2, y),
                return_text,
                fill=color,
                font=self.font_medium
            )
        else:
            draw.text(
                (x_center - ticker_width // 2, y),
                ticker_return,
                fill=color,
                font=self.font_medium
            )

    def generate(self, share_data: Dict) -> bytes:
        """
        Generate PNG image bytes from share data.

        Args:
            share_data: Dictionary containing:
                - portfolio_return_pct: float
                - best_benchmark_ticker: str
                - best_benchmark_return_pct: float
                - worst_benchmark_ticker: str
                - worst_benchmark_return_pct: float
                - opportunity_cost_pct: float

        Returns:
            PNG image as bytes
        """
        # Create image
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Current y position
        y = self.PADDING

        # Header: "HONEST PORTFOLIO"
        self._draw_centered_text(
            draw,
            "HONEST PORTFOLIO",
            y,
            self.font_title,
            self.HEADER_COLOR
        )

        # Your Return section
        y += 100
        self._draw_centered_text(
            draw,
            "YOUR RETURN",
            y,
            self.font_label,
            self.LABEL_COLOR
        )

        y += 45
        portfolio_return_pct = share_data.get('portfolio_return_pct', 0)
        return_text = self._format_percentage(portfolio_return_pct)
        return_color = self._get_color_for_value(portfolio_return_pct)
        self._draw_centered_text(
            draw,
            return_text,
            y,
            self.font_large,
            return_color
        )

        # Divider
        y += 100
        self._draw_divider(draw, y)

        # Benchmarks section
        y += 40

        # Two columns for best and worst
        left_x = self.WIDTH // 4
        right_x = 3 * self.WIDTH // 4

        self._draw_benchmark_column(
            draw,
            "BEST BENCHMARK",
            share_data.get('best_benchmark_ticker', 'N/A'),
            share_data.get('best_benchmark_return_pct', 0),
            left_x,
            y
        )

        self._draw_benchmark_column(
            draw,
            "WORST BENCHMARK",
            share_data.get('worst_benchmark_ticker', 'N/A'),
            share_data.get('worst_benchmark_return_pct', 0),
            right_x,
            y
        )

        # Divider
        y += 140
        self._draw_divider(draw, y)

        # Opportunity Cost section
        y += 40
        self._draw_centered_text(
            draw,
            "OPPORTUNITY COST",
            y,
            self.font_label,
            self.LABEL_COLOR
        )

        y += 45
        opportunity_cost = share_data.get('opportunity_cost_pct', 0)
        best_ticker = share_data.get('best_benchmark_ticker', 'BEST')

        # Show opportunity cost vs best benchmark
        opp_text = f"{self._format_percentage(opportunity_cost)} vs {best_ticker}"
        opp_color = self._get_color_for_value(opportunity_cost)

        self._draw_centered_text(
            draw,
            opp_text,
            y,
            self.font_medium,
            opp_color,
            max_width=self.WIDTH - self.PADDING * 2
        )

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
