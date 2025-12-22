"""Yahoo Finance data source implementation."""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from opa_quotes_streamer.models.quote import Quote
from opa_quotes_streamer.sources.base import BaseDataSource
from opa_quotes_streamer.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class YFinanceError(Exception):
    """Exception raised for Yahoo Finance specific errors."""
    pass


class YFinanceSource(BaseDataSource):
    """Yahoo Finance data source with rate limiting and retry logic.
    
    Fetches real-time quotes from Yahoo Finance API with:
    - Rate limiting (default 2000 requests/hour)
    - Exponential backoff retry on failures
    - Automatic conversion to Quote model
    - Error handling and logging
    
    Attributes:
        rate_limiter: RateLimiter instance for API throttling
        max_retries: Maximum retry attempts for failed requests
        
    Example:
        >>> source = YFinanceSource(max_requests_per_hour=2000)
        >>> quotes = await source.fetch_quotes(["AAPL", "MSFT"])
        >>> await source.close()
    """
    
    def __init__(
        self,
        max_requests_per_hour: int = 2000,
        max_retries: int = 3
    ):
        """Initialize Yahoo Finance source.
        
        Args:
            max_requests_per_hour: Maximum API requests per hour
            max_retries: Maximum number of retry attempts
        """
        self.rate_limiter = RateLimiter(max_requests_per_hour=max_requests_per_hour)
        self.max_retries = max_retries
        logger.info(
            f"YFinanceSource initialized with rate limit: {max_requests_per_hour} req/h"
        )
    
    async def fetch_quotes(self, tickers: List[str]) -> List[Quote]:
        """Fetch quotes for given tickers from Yahoo Finance.
        
        Args:
            tickers: List of ticker symbols to fetch
            
        Returns:
            List of Quote objects with latest data
            
        Raises:
            YFinanceError: If fetching fails after all retries
        """
        if not tickers:
            logger.warning("No tickers provided to fetch_quotes")
            return []
        
        logger.info(f"Fetching quotes for {len(tickers)} tickers: {tickers}")
        
        try:
            # Acquire rate limiter token
            await self.rate_limiter.acquire()
            
            # Fetch with retry logic
            quotes = await self._fetch_with_retry(tickers)
            
            logger.info(f"Successfully fetched {len(quotes)} quotes")
            return quotes
            
        except Exception as e:
            logger.error(f"Failed to fetch quotes for {tickers}: {e}", exc_info=True)
            raise YFinanceError(f"Failed to fetch quotes: {e}") from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    async def _fetch_with_retry(self, tickers: List[str]) -> List[Quote]:
        """Fetch quotes with exponential backoff retry.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            List of Quote objects
            
        Raises:
            Exception: If fetching fails after retries
        """
        # Run yfinance in thread pool (it's blocking I/O)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            self._fetch_yfinance_data,
            tickers
        )
        
        # Convert to Quote objects
        quotes = self._convert_to_quotes(data, tickers)
        return quotes
    
    def _fetch_yfinance_data(self, tickers: List[str]) -> pd.DataFrame:
        """Fetch data from yfinance (blocking call).
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            DataFrame with quote data
            
        Raises:
            YFinanceError: If fetching fails
        """
        try:
            # Download latest quotes (1 day period, 1 minute interval)
            tickers_str = " ".join(tickers)
            data = yf.download(
                tickers_str,
                period="1d",
                interval="1m",
                progress=False,
                show_errors=False,
                threads=True
            )
            
            if data.empty:
                logger.warning(f"yfinance returned empty data for {tickers}")
                return pd.DataFrame()
            
            return data
            
        except Exception as e:
            logger.error(f"yfinance.download failed: {e}")
            raise YFinanceError(f"yfinance download error: {e}") from e
    
    def _convert_to_quotes(
        self,
        data: pd.DataFrame,
        tickers: List[str]
    ) -> List[Quote]:
        """Convert yfinance DataFrame to Quote objects.
        
        Args:
            data: yfinance DataFrame
            tickers: List of ticker symbols
            
        Returns:
            List of Quote objects
        """
        quotes = []
        
        if data.empty:
            return quotes
        
        try:
            # Get latest row (most recent data)
            latest_data = data.tail(1)
            
            for ticker in tickers:
                try:
                    quote = self._create_quote_from_data(ticker, latest_data, data)
                    if quote:
                        quotes.append(quote)
                except Exception as e:
                    logger.error(f"Failed to create quote for {ticker}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error converting data to quotes: {e}")
        
        return quotes
    
    def _create_quote_from_data(
        self,
        ticker: str,
        latest_data: pd.DataFrame,
        full_data: pd.DataFrame
    ) -> Optional[Quote]:
        """Create a Quote object from yfinance data.
        
        Args:
            ticker: Ticker symbol
            latest_data: Latest row from DataFrame
            full_data: Full DataFrame for additional data
            
        Returns:
            Quote object or None if data insufficient
        """
        try:
            # Handle multi-index columns (multiple tickers)
            if isinstance(latest_data.columns, pd.MultiIndex):
                close = latest_data[('Close', ticker)].iloc[0]
                volume = latest_data[('Volume', ticker)].iloc[0]
                
                # Optional fields
                open_price = latest_data.get(('Open', ticker))
                high = latest_data.get(('High', ticker))
                low = latest_data.get(('Low', ticker))
            else:
                # Single ticker case
                close = latest_data['Close'].iloc[0]
                volume = latest_data['Volume'].iloc[0]
                
                open_price = latest_data.get('Open')
                high = latest_data.get('High')
                low = latest_data.get('Low')
            
            # Validate essential data
            if pd.isna(close) or pd.isna(volume):
                logger.warning(f"Missing essential data for {ticker}")
                return None
            
            # Get previous close (if available)
            previous_close = None
            if len(full_data) > 1:
                prev_data = full_data.tail(2).head(1)
                if isinstance(prev_data.columns, pd.MultiIndex):
                    prev_close_val = prev_data[('Close', ticker)].iloc[0]
                else:
                    prev_close_val = prev_data['Close'].iloc[0]
                if not pd.isna(prev_close_val):
                    previous_close = float(prev_close_val)
            
            # Create Quote
            quote = Quote(
                ticker=ticker,
                price=float(close),
                volume=int(volume),
                timestamp=datetime.now(timezone.utc),
                source="yfinance",
                open=float(open_price.iloc[0]) if open_price is not None and not pd.isna(open_price.iloc[0]) else None,
                high=float(high.iloc[0]) if high is not None and not pd.isna(high.iloc[0]) else None,
                low=float(low.iloc[0]) if low is not None and not pd.isna(low.iloc[0]) else None,
                previous_close=previous_close
            )
            
            logger.debug(f"Created quote for {ticker}: price={quote.price}, volume={quote.volume}")
            return quote
            
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error extracting data for {ticker}: {e}")
            return None
    
    async def close(self) -> None:
        """Close any open connections or resources.
        
        Currently no resources to close for yfinance.
        """
        logger.info("YFinanceSource closed")
