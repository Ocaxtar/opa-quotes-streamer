"""Base interface for publishers."""

from abc import ABC, abstractmethod
from typing import List
from opa_quotes_streamer.models.quote import Quote


class BasePublisher(ABC):
    """Abstract base class for publishers.
    
    All publishers must implement this interface to provide
    consistent quote publishing functionality.
    
    Example:
        >>> class MyPublisher(BasePublisher):
        ...     async def publish_batch(self, quotes: List[Quote]) -> int:
        ...         # Implementation here
        ...         pass
    """
    
    @abstractmethod
    async def publish_batch(self, quotes: List[Quote]) -> int:
        """Publish a batch of quotes.
        
        Args:
            quotes: List of Quote objects to publish
            
        Returns:
            Number of quotes successfully published
            
        Raises:
            Exception: If publishing fails
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close any open connections or resources.
        
        Should be called when shutting down the publisher.
        """
        pass
