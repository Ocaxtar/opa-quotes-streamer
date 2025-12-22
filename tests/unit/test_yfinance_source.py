"""Unit tests for YFinanceSource."""

import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from opa_quotes_streamer.sources.yfinance_source import YFinanceSource, YFinanceError
from opa_quotes_streamer.models.quote import Quote


class TestYFinanceSource:
    """Test suite for YFinanceSource class."""
    
    def test_init_default_params(self):
        """Test initialization with default parameters."""
        source = YFinanceSource()
        
        assert source.rate_limiter is not None
        assert source.max_retries == 3
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        source = YFinanceSource(max_requests_per_hour=1000, max_retries=5)
        
        assert source.rate_limiter.capacity == 1000
        assert source.max_retries == 5
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_empty_tickers(self):
        """Test fetch_quotes with empty ticker list."""
        source = YFinanceSource()
        
        quotes = await source.fetch_quotes([])
        
        assert quotes == []
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_success_single_ticker(self):
        """Test successful quote fetching for single ticker."""
        source = YFinanceSource()
        
        # Mock yfinance data
        mock_data = pd.DataFrame({
            'Close': [178.45],
            'Volume': [52341000],
            'Open': [175.20],
            'High': [179.00],
            'Low': [174.50]
        })
        
        with patch.object(source, '_fetch_yfinance_data', return_value=mock_data):
            quotes = await source.fetch_quotes(["AAPL"])
        
        assert len(quotes) == 1
        assert quotes[0].ticker == "AAPL"
        assert quotes[0].price == 178.45
        assert quotes[0].volume == 52341000
        assert quotes[0].source == "yfinance"
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_success_multiple_tickers(self):
        """Test successful quote fetching for multiple tickers."""
        source = YFinanceSource()
        
        # Mock yfinance data with MultiIndex columns
        columns = pd.MultiIndex.from_product(
            [['Close', 'Volume', 'Open', 'High', 'Low'], ['AAPL', 'MSFT']]
        )
        mock_data = pd.DataFrame(
            [[178.45, 350.20, 52341000, 89234000, 175.20, 348.50, 179.00, 352.00, 174.50, 347.00]],
            columns=columns
        )
        
        with patch.object(source, '_fetch_yfinance_data', return_value=mock_data):
            quotes = await source.fetch_quotes(["AAPL", "MSFT"])
        
        assert len(quotes) == 2
        
        aapl_quote = next(q for q in quotes if q.ticker == "AAPL")
        assert aapl_quote.price == 178.45
        assert aapl_quote.volume == 52341000
        
        msft_quote = next(q for q in quotes if q.ticker == "MSFT")
        assert msft_quote.price == 350.20
        assert msft_quote.volume == 89234000
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_with_rate_limiting(self):
        """Test that rate limiter is called before fetching."""
        source = YFinanceSource(max_requests_per_hour=10)
        
        mock_data = pd.DataFrame({
            'Close': [178.45],
            'Volume': [52341000]
        })
        
        with patch.object(source.rate_limiter, 'acquire', new_callable=AsyncMock) as mock_acquire, \
             patch.object(source, '_fetch_yfinance_data', return_value=mock_data):
            
            await source.fetch_quotes(["AAPL"])
            
            mock_acquire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_empty_dataframe(self):
        """Test handling of empty DataFrame from yfinance."""
        source = YFinanceSource()
        
        empty_data = pd.DataFrame()
        
        with patch.object(source, '_fetch_yfinance_data', return_value=empty_data):
            quotes = await source.fetch_quotes(["INVALID"])
        
        assert quotes == []
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_missing_data(self):
        """Test handling of missing essential data (NaN values)."""
        source = YFinanceSource()
        
        # Data with NaN values
        mock_data = pd.DataFrame({
            'Close': [pd.NA],
            'Volume': [pd.NA]
        })
        
        with patch.object(source, '_fetch_yfinance_data', return_value=mock_data):
            quotes = await source.fetch_quotes(["AAPL"])
        
        assert quotes == []
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_yfinance_error(self):
        """Test error handling when yfinance fails."""
        source = YFinanceSource()
        
        with patch.object(source, '_fetch_yfinance_data', side_effect=Exception("API Error")):
            with pytest.raises(YFinanceError, match="Failed to fetch quotes"):
                await source.fetch_quotes(["AAPL"])
    
    def test_fetch_yfinance_data_success(self):
        """Test _fetch_yfinance_data with mocked yfinance.download."""
        source = YFinanceSource()
        
        mock_df = pd.DataFrame({
            'Close': [178.45],
            'Volume': [52341000]
        })
        
        with patch('opa_quotes_streamer.sources.yfinance_source.yf.download', return_value=mock_df):
            result = source._fetch_yfinance_data(["AAPL"])
        
        assert not result.empty
        assert 'Close' in result.columns
    
    def test_fetch_yfinance_data_empty_result(self):
        """Test _fetch_yfinance_data when yfinance returns empty."""
        source = YFinanceSource()
        
        empty_df = pd.DataFrame()
        
        with patch('opa_quotes_streamer.sources.yfinance_source.yf.download', return_value=empty_df):
            result = source._fetch_yfinance_data(["INVALID"])
        
        assert result.empty
    
    def test_fetch_yfinance_data_exception(self):
        """Test _fetch_yfinance_data when yfinance raises exception."""
        source = YFinanceSource()
        
        with patch('opa_quotes_streamer.sources.yfinance_source.yf.download', side_effect=Exception("Network error")):
            with pytest.raises(YFinanceError, match="yfinance download error"):
                source._fetch_yfinance_data(["AAPL"])
    
    def test_convert_to_quotes_single_ticker(self):
        """Test conversion of DataFrame to Quote objects (single ticker)."""
        source = YFinanceSource()
        
        data = pd.DataFrame({
            'Close': [178.45],
            'Volume': [52341000],
            'Open': [175.20],
            'High': [179.00],
            'Low': [174.50]
        })
        
        quotes = source._convert_to_quotes(data, ["AAPL"])
        
        assert len(quotes) == 1
        assert quotes[0].ticker == "AAPL"
        assert quotes[0].price == 178.45
    
    def test_convert_to_quotes_multiple_tickers(self):
        """Test conversion with MultiIndex DataFrame (multiple tickers)."""
        source = YFinanceSource()
        
        columns = pd.MultiIndex.from_product(
            [['Close', 'Volume'], ['AAPL', 'MSFT']]
        )
        data = pd.DataFrame(
            [[178.45, 350.20, 52341000, 89234000]],
            columns=columns
        )
        
        quotes = source._convert_to_quotes(data, ["AAPL", "MSFT"])
        
        assert len(quotes) == 2
    
    def test_convert_to_quotes_empty_dataframe(self):
        """Test conversion with empty DataFrame."""
        source = YFinanceSource()
        
        empty_df = pd.DataFrame()
        quotes = source._convert_to_quotes(empty_df, ["AAPL"])
        
        assert quotes == []
    
    def test_create_quote_from_data_valid(self):
        """Test creating Quote from valid data."""
        source = YFinanceSource()
        
        data = pd.DataFrame({
            'Close': [178.45],
            'Volume': [52341000],
            'Open': [175.20],
            'High': [179.00],
            'Low': [174.50]
        })
        
        quote = source._create_quote_from_data("AAPL", data, data)
        
        assert quote is not None
        assert quote.ticker == "AAPL"
        assert quote.price == 178.45
        assert quote.volume == 52341000
        assert quote.open == 175.20
        assert quote.high == 179.00
        assert quote.low == 174.50
    
    def test_create_quote_from_data_missing_values(self):
        """Test creating Quote with missing essential values."""
        source = YFinanceSource()
        
        data = pd.DataFrame({
            'Close': [pd.NA],
            'Volume': [pd.NA]
        })
        
        quote = source._create_quote_from_data("AAPL", data, data)
        
        assert quote is None
    
    def test_create_quote_from_data_with_previous_close(self):
        """Test creating Quote with previous close data."""
        source = YFinanceSource()
        
        # Two rows for previous close calculation
        data = pd.DataFrame({
            'Close': [177.80, 178.45],
            'Volume': [50000000, 52341000]
        })
        
        latest = data.tail(1)
        quote = source._create_quote_from_data("AAPL", latest, data)
        
        assert quote is not None
        assert quote.previous_close == 177.80
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        source = YFinanceSource()
        
        # Should not raise any exception
        await source.close()
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_partial_failure(self):
        """Test handling when some tickers fail but others succeed."""
        source = YFinanceSource()
        
        # Mock data where one ticker has valid data, another doesn't
        columns = pd.MultiIndex.from_product(
            [['Close', 'Volume'], ['AAPL', 'INVALID']]
        )
        mock_data = pd.DataFrame(
            [[178.45, pd.NA, 52341000, pd.NA]],
            columns=columns
        )
        
        with patch.object(source, '_fetch_yfinance_data', return_value=mock_data):
            quotes = await source.fetch_quotes(["AAPL", "INVALID"])
        
        # Only AAPL should be in quotes
        assert len(quotes) == 1
        assert quotes[0].ticker == "AAPL"
    
    @pytest.mark.asyncio
    async def test_integration_with_real_rate_limiter(self):
        """Test integration with real RateLimiter (not mocked)."""
        source = YFinanceSource(max_requests_per_hour=3600)  # 1 per second
        
        mock_data = pd.DataFrame({
            'Close': [178.45],
            'Volume': [52341000]
        })
        
        with patch.object(source, '_fetch_yfinance_data', return_value=mock_data):
            # Should not raise and should respect rate limit
            quotes = await source.fetch_quotes(["AAPL"])
        
        assert len(quotes) == 1
        assert source.rate_limiter.available_tokens() < 3600
