"""Tests for Quote model contract validation (INV-002, INV-003, INV-005)."""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from opa_quotes_streamer.models.quote import Quote


class TestQuoteContractValidation:
    """Test contract invariants for Quote model."""
    
    def test_ticker_format_valid_single_char(self):
        """INV-002: Single character ticker valid."""
        quote = Quote(
            ticker="A",
            price=100.0,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="yfinance"
        )
        assert quote.ticker == "A"
    
    def test_ticker_format_valid_five_chars(self):
        """INV-002: Five character ticker valid."""
        quote = Quote(
            ticker="GOOGL",
            price=100.0,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="yfinance"
        )
        assert quote.ticker == "GOOGL"
    
    def test_ticker_format_valid_common_tickers(self):
        """INV-002: Common ticker formats."""
        valid_tickers = ["AAPL", "MSFT", "TSLA", "AMD", "NVDA"]
        for ticker in valid_tickers:
            quote = Quote(
                ticker=ticker,
                price=100.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
            assert quote.ticker == ticker.upper()
    
    def test_ticker_format_auto_uppercase(self):
        """INV-002: Lowercase ticker auto-converted to uppercase."""
        quote = Quote(
            ticker="aapl",
            price=100.0,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="yfinance"
        )
        assert quote.ticker == "AAPL"
    
    def test_ticker_format_invalid_too_long(self):
        """INV-002: Ticker longer than 5 chars rejected."""
        with pytest.raises(ValidationError, match="Invalid ticker format"):
            Quote(
                ticker="TOOLONG",
                price=100.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
    
    def test_ticker_format_invalid_empty(self):
        """INV-002: Empty ticker rejected."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            Quote(
                ticker="",
                price=100.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
    
    def test_ticker_format_invalid_with_numbers(self):
        """INV-002: Ticker with numbers rejected."""
        with pytest.raises(ValidationError, match="Invalid ticker format"):
            Quote(
                ticker="A123",
                price=100.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
    
    def test_ticker_format_invalid_with_special_chars(self):
        """INV-002: Ticker with special characters rejected."""
        with pytest.raises(ValidationError, match="Invalid ticker format"):
            Quote(
                ticker="AA-PL",
                price=100.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
    
    def test_timestamp_utc_valid(self):
        """INV-003: UTC timestamp accepted."""
        utc_time = datetime.now(timezone.utc)
        quote = Quote(
            ticker="AAPL",
            price=100.0,
            volume=1000,
            timestamp=utc_time,
            source="yfinance"
        )
        assert quote.timestamp.tzinfo == timezone.utc
    
    def test_timestamp_non_utc_rejected(self):
        """INV-003: Non-UTC timestamp rejected."""
        est = timezone(timedelta(hours=-5))
        non_utc_time = datetime.now(est)
        
        with pytest.raises(ValidationError, match="Timestamp must be UTC"):
            Quote(
                ticker="AAPL",
                price=100.0,
                volume=1000,
                timestamp=non_utc_time,
                source="yfinance"
            )
    
    def test_timestamp_naive_rejected(self):
        """INV-003: Naive timestamp (no timezone) rejected."""
        naive_time = datetime.now()
        
        with pytest.raises(ValidationError, match="Timestamp must have timezone"):
            Quote(
                ticker="AAPL",
                price=100.0,
                volume=1000,
                timestamp=naive_time,
                source="yfinance"
            )
    
    def test_source_valid_yfinance(self):
        """INV-005: Valid source 'yfinance'."""
        quote = Quote(
            ticker="AAPL",
            price=100.0,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="yfinance"
        )
        assert quote.source == "yfinance"
    
    def test_source_valid_fmp(self):
        """INV-005: Valid source 'fmp'."""
        quote = Quote(
            ticker="AAPL",
            price=100.0,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="fmp"
        )
        assert quote.source == "fmp"
    
    def test_source_valid_manual(self):
        """INV-005: Valid source 'manual'."""
        quote = Quote(
            ticker="AAPL",
            price=100.0,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="manual"
        )
        assert quote.source == "manual"
    
    def test_source_auto_lowercase(self):
        """INV-005: Uppercase source auto-converted to lowercase."""
        quote = Quote(
            ticker="AAPL",
            price=100.0,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="YFINANCE"
        )
        assert quote.source == "yfinance"
    
    def test_source_invalid(self):
        """INV-005: Invalid source rejected."""
        with pytest.raises(ValidationError, match="Invalid source"):
            Quote(
                ticker="AAPL",
                price=100.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="invalid_source"
            )
    
    def test_source_empty_rejected(self):
        """INV-005: Empty source rejected."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            Quote(
                ticker="AAPL",
                price=100.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source=""
            )
    
    def test_price_positive(self):
        """INV-004: Positive price accepted."""
        quote = Quote(
            ticker="AAPL",
            price=178.45,
            volume=1000,
            timestamp=datetime.now(timezone.utc),
            source="yfinance"
        )
        assert quote.price == 178.45
    
    def test_price_negative_rejected(self):
        """INV-004: Negative price rejected."""
        with pytest.raises(ValidationError):
            Quote(
                ticker="AAPL",
                price=-10.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
    
    def test_price_zero_rejected(self):
        """INV-004: Zero price rejected."""
        with pytest.raises(ValidationError):
            Quote(
                ticker="AAPL",
                price=0.0,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
