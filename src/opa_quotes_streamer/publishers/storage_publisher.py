"""Storage publisher for sending quotes to opa-quotes-storage."""

import logging
from typing import List, Dict, Any
import httpx

from opa_quotes_streamer.models.quote import Quote
from opa_quotes_streamer.publishers.base import BasePublisher
from opa_quotes_streamer.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)


class PublisherError(Exception):
    """Exception raised for publisher-specific errors."""
    pass


class StoragePublisher(BasePublisher):
    """Publisher for sending quote batches to opa-quotes-storage via HTTP.
    
    Sends batches of quotes to the storage service with:
    - Circuit breaker pattern for fault tolerance
    - Configurable timeout
    - Automatic retry handling via circuit breaker
    - Detailed logging
    
    Attributes:
        storage_url: Base URL of opa-quotes-storage service
        timeout: HTTP request timeout in seconds
        circuit_breaker: CircuitBreaker instance for resilience
        
    Example:
        >>> publisher = StoragePublisher("http://localhost:8000", timeout=10)
        >>> result = await publisher.publish_batch(quotes)
        >>> print(f"Published {result['inserted']} quotes")
        >>> await publisher.close()
    """
    
    def __init__(
        self,
        storage_url: str,
        timeout: int = 10,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        """Initialize storage publisher.
        
        Args:
            storage_url: Base URL of opa-quotes-storage (e.g., "http://localhost:8000")
            timeout: HTTP request timeout in seconds
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_timeout: Seconds before circuit half-opens
        """
        self.storage_url = storage_url.rstrip('/')
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            timeout=circuit_breaker_timeout,
            name="storage-publisher"
        )
        logger.info(
            f"StoragePublisher initialized: storage_url={storage_url}, "
            f"timeout={timeout}s, circuit_breaker_threshold={circuit_breaker_threshold}"
        )
    
    async def publish_batch(self, quotes: List[Quote]) -> int:
        """Publish a batch of quotes to storage service.
        
        Args:
            quotes: List of Quote objects to publish
            
        Returns:
            Number of quotes successfully published
            
        Raises:
            PublisherError: If publishing fails after circuit breaker logic
        """
        if not quotes:
            logger.warning("publish_batch called with empty quotes list")
            return 0
        
        logger.info(f"Publishing batch of {len(quotes)} quotes to storage")
        
        try:
            # Use circuit breaker for resilience
            result = await self.circuit_breaker.call(
                lambda: self._post_quotes(quotes)
            )
            
            inserted = result.get('inserted', 0)
            errors = result.get('errors', 0)
            
            logger.info(
                f"Batch published successfully: {inserted} inserted, {errors} errors"
            )
            
            return inserted
            
        except CircuitBreakerOpenError as e:
            logger.error(f"Circuit breaker is OPEN, rejecting publish: {e}")
            raise PublisherError(
                "Storage service unavailable (circuit breaker OPEN)"
            ) from e
            
        except Exception as e:
            logger.error(
                f"Failed to publish batch of {len(quotes)} quotes: {e}",
                exc_info=True
            )
            raise PublisherError(f"Storage publish failed: {e}") from e
    
    async def _post_quotes(self, quotes: List[Quote]) -> Dict[str, Any]:
        """POST quotes to storage API (internal method).
        
        Args:
            quotes: List of Quote objects
            
        Returns:
            Response JSON with 'inserted' and 'errors' counts
            
        Raises:
            httpx.HTTPStatusError: If HTTP request fails
            httpx.RequestError: If network request fails
        """
        # Convert quotes to dict format
        quotes_data = [q.model_dump(mode='json') for q in quotes]
        payload = {"quotes": quotes_data}
        
        logger.debug(f"Posting {len(quotes_data)} quotes to {self.storage_url}/v1/quotes/batch")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.storage_url}/v1/quotes/batch",
                    json=payload
                )
                
                # Raise exception for 4xx/5xx status codes
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Storage response: {result}")
                
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error from storage: status={e.response.status_code}, "
                    f"body={e.response.text}"
                )
                raise
                
            except httpx.RequestError as e:
                logger.error(f"Network error connecting to storage: {e}")
                raise
    
    async def close(self) -> None:
        """Close any open connections or resources.
        
        Currently no persistent resources to close.
        """
        logger.info("StoragePublisher closed")
    
    def get_circuit_state(self) -> str:
        """Get current circuit breaker state.
        
        Returns:
            Circuit state as string ("closed", "open", "half_open")
        """
        return self.circuit_breaker.get_state().value
    
    def reset_circuit(self) -> None:
        """Manually reset circuit breaker to CLOSED state.
        
        Use this to force-reopen the circuit after manual intervention.
        """
        logger.info("Manually resetting circuit breaker")
        self.circuit_breaker.reset()
