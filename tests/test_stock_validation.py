"""
Tests for the validate_ticker() function from app.services.stock_data.

This test suite verifies that ticker validation works correctly for:
1. ETFs like SPY (the key bug fix - ETFs should pass validation)
2. All comparison stocks (fast path via ComparisonStock table)
3. Invalid/fake tickers (should fail validation)

The validation function has two code paths:
- Fast path: Tickers in the ComparisonStock table are immediately valid
- yfinance path: Other tickers are validated via yf.download()
"""
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from app.services.stock_data import validate_ticker


class TestTickerValidation:
    """Test suite for the validate_ticker() function."""

    def test_spy_etf_passes_validation_via_fast_path(
        self, app, db_session, seed_comparison_stocks
    ):
        """
        Test that SPY (an ETF) passes validation via the fast path.

        This is the key bug fix test - SPY is a comparison stock and should
        be validated via the fast path without needing yfinance calls.
        ETFs were previously failing validation when using yf.Ticker().info
        because ETFs don't have all the same info fields as stocks.
        """
        with app.app_context():
            result = validate_ticker('SPY')

        assert result is True, (
            "SPY (S&P 500 ETF) should pass validation via fast path "
            "since it is a comparison stock"
        )

    def test_spy_etf_case_insensitive(
        self, app, db_session, seed_comparison_stocks
    ):
        """
        Test that ticker validation is case-insensitive.

        The validate_ticker function should convert to uppercase before checking.
        """
        with app.app_context():
            result_lower = validate_ticker('spy')
            result_mixed = validate_ticker('Spy')

        assert result_lower is True, "Lowercase 'spy' should pass validation"
        assert result_mixed is True, "Mixed case 'Spy' should pass validation"

    def test_all_comparison_stocks_pass_validation(
        self, app, db_session, seed_comparison_stocks
    ):
        """
        Test that all default comparison stocks pass validation via fast path.

        These tickers should all be validated immediately without yfinance calls
        since they exist in the ComparisonStock table.
        """
        comparison_tickers = ['SPY', 'AAPL', 'META', 'GOOGL', 'NVDA', 'AMZN']

        with app.app_context():
            for ticker in comparison_tickers:
                result = validate_ticker(ticker)
                assert result is True, (
                    f"Comparison stock {ticker} should pass validation via fast path"
                )

    def test_invalid_ticker_fails_validation(self, app, db_session):
        """
        Test that invalid/fake tickers fail validation.

        When a ticker is not in the ComparisonStock table and yfinance
        returns no data, validation should return False.
        """
        with patch('app.services.stock_data.yf.download') as mock_download:
            # Simulate yfinance returning empty DataFrame for invalid ticker
            mock_download.return_value = pd.DataFrame()

            with app.app_context():
                result = validate_ticker('XYZNOTREAL123')

            assert result is False, (
                "Invalid ticker 'XYZNOTREAL123' should fail validation"
            )
            # Verify yfinance was called since ticker is not a comparison stock
            mock_download.assert_called_once()

    def test_ticker_with_no_close_column_fails_validation(self, app, db_session):
        """
        Test that a ticker returning data without 'Close' column fails validation.

        This covers edge cases where yfinance returns malformed data.
        """
        with patch('app.services.stock_data.yf.download') as mock_download:
            # Simulate yfinance returning DataFrame without 'Close' column
            mock_download.return_value = pd.DataFrame({'Open': [100.0]})

            with app.app_context():
                result = validate_ticker('BADDATA')

            assert result is False, (
                "Ticker with missing 'Close' column should fail validation"
            )

    def test_yfinance_exception_returns_false(self, app, db_session):
        """
        Test that yfinance exceptions are handled gracefully.

        If yfinance raises an exception during validation, the function
        should return False rather than propagating the exception.
        """
        with patch('app.services.stock_data.yf.download') as mock_download:
            # Simulate yfinance raising an exception
            mock_download.side_effect = Exception("Network error")

            with app.app_context():
                result = validate_ticker('ERRORSTOCK')

            assert result is False, (
                "Ticker validation should return False on yfinance exception"
            )

    def test_valid_non_comparison_stock_passes_via_yfinance(
        self, app, db_session
    ):
        """
        Test that valid stocks not in comparison list pass via yfinance path.

        Stocks that are not comparison stocks should be validated through
        yfinance. This tests the fallback path when fast path doesn't match.
        """
        with patch('app.services.stock_data.yf.download') as mock_download:
            # Simulate yfinance returning valid data
            mock_download.return_value = pd.DataFrame({
                'Close': [150.0, 151.0, 152.0, 153.0, 154.0]
            })

            with app.app_context():
                result = validate_ticker('MSFT')

            assert result is True, (
                "Valid non-comparison stock should pass validation via yfinance"
            )
            # Verify yfinance was called with correct parameters
            mock_download.assert_called_once_with(
                'MSFT', period='5d', progress=False
            )

    def test_fast_path_does_not_call_yfinance(
        self, app, db_session, seed_comparison_stocks
    ):
        """
        Test that the fast path for comparison stocks does not call yfinance.

        When a ticker is found in the ComparisonStock table, yfinance
        should not be called at all (optimization).
        """
        with patch('app.services.stock_data.yf.download') as mock_download:
            with app.app_context():
                result = validate_ticker('AAPL')

            assert result is True
            mock_download.assert_not_called(), (
                "yfinance should not be called for comparison stocks"
            )

    def test_empty_ticker_fails_validation(self, app, db_session):
        """
        Test that empty ticker string fails validation.

        Edge case to ensure empty strings don't cause unexpected behavior.
        """
        with patch('app.services.stock_data.yf.download') as mock_download:
            # Empty ticker should result in empty data
            mock_download.return_value = pd.DataFrame()

            with app.app_context():
                result = validate_ticker('')

            assert result is False, "Empty ticker string should fail validation"

    def test_etf_passes_via_yfinance_path(self, app, db_session):
        """
        Test that ETFs not in comparison list pass validation via yfinance.

        This tests that the yf.download() approach works for ETFs (unlike
        the old yf.Ticker().info approach that failed for ETFs).
        """
        with patch('app.services.stock_data.yf.download') as mock_download:
            # Simulate yfinance returning valid ETF data
            mock_download.return_value = pd.DataFrame({
                'Close': [400.0, 401.0, 402.0, 403.0, 404.0]
            })

            with app.app_context():
                # QQQ is an ETF not in the default comparison stocks
                result = validate_ticker('QQQ')

            assert result is True, (
                "ETFs should pass validation via yfinance download path"
            )
