"""Base interface for data sources."""

from abc import ABC, abstractmethod
from typing import List
from opa_quotes_streamer.models.quote import Quote


class BaseDataSource(ABC):
    """Abstract base class for data sources.
    
    All data sources must implement this interface to provide
    consistent quote fetching functionality.
    
    Example:
        >>> class MyDataSource(BaseDataSource):
        ...     async def fetch_quotes(self, tickers: List[str]) -> List[Quote]:
        ...         # Implementation here
        ...         pass
    """
    
    @abstractmethod
    async def fetch_quotes(self, tickers: List[str]) -> List[Quote]:
        """Fetch quotes for given tickers.
        
        Args:
            tickers: List of ticker symbols to fetch
            
        Returns:
            List of Quote objects
            
        Raises:
            Exception: If fetching fails
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close any open connections or resources.
        
        Should be called when shutting down the data source.
        """
        pass
