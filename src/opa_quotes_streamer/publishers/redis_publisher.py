"""Redis Pub/Sub publisher for real-time quotes."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import redis.asyncio as redis
from prometheus_client import Counter, Histogram

from opa_quotes_streamer.models.quote import Quote
from opa_quotes_streamer.publishers.base import BasePublisher
from opa_quotes_streamer.utils.circuit_breaker import CircuitBreaker


# Prometheus metrics
REDIS_PUBLISHES_TOTAL = Counter(
    'redis_publishes_total',
    'Total number of Redis publish operations',
    ['status']
)

REDIS_PUBLISH_ERRORS_TOTAL = Counter(
    'redis_publish_errors_total',
    'Total number of Redis publish errors',
    ['error_type']
)

REDIS_PUBLISH_LATENCY_SECONDS = Histogram(
    'redis_publish_latency_seconds',
    'Redis publish operation latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)


logger = logging.getLogger(__name__)


class RedisPublisher(BasePublisher):
    """Publisher for streaming quotes to Redis Pub/Sub.
    
    Publishes quotes in CloudEvents 1.0 format to Redis channels.
    Includes circuit breaker for resilience against Redis failures.
    
    CloudEvents format:
        {
            "specversion": "1.0",
            "type": "com.opamachine.quotes.price-updated",
            "source": "opa-quotes-streamer",
            "id": "uuid",
            "time": "ISO 8601",
            "datacontenttype": "application/json",
            "data": {
                "ticker": "AAPL",
                "price": 189.75,
                ...
            }
        }
    
    Attributes:
        redis_url: Redis connection URL (default: redis://localhost:6381)
        channel: Redis channel name (default: quotes-stream)
        circuit_breaker: Circuit breaker for Redis operations
    
    Example:
        >>> publisher = RedisPublisher("redis://localhost:6381")
        >>> await publisher.publish_batch([quote1, quote2])
        2
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6381",
        channel: str = "quotes-stream",
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """Initialize Redis publisher.
        
        Args:
            redis_url: Redis connection URL
            channel: Redis channel to publish to
            circuit_breaker: Optional circuit breaker instance
        """
        self.redis_url = redis_url
        self.channel = channel
        self._client: Optional[redis.Redis] = None
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=5,
            timeout=30.0
        )
        logger.info(f"RedisPublisher initialized: url={redis_url}, channel={channel}")
    
    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client.
        
        Returns:
            Redis client instance
            
        Raises:
            redis.RedisError: If connection fails
        """
        if self._client is None:
            try:
                self._client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._client
    
    def _quote_to_cloudevent(self, quote: Quote) -> dict:
        """Convert Quote to CloudEvents 1.0 format.
        
        Args:
            quote: Quote object to convert
            
        Returns:
            CloudEvents formatted dictionary
        """
        return {
            "specversion": "1.0",
            "type": "com.opamachine.quotes.price-updated",
            "source": "opa-quotes-streamer",
            "id": str(uuid4()),
            "time": datetime.now(timezone.utc).isoformat(),
            "datacontenttype": "application/json",
            "data": {
                "ticker": quote.ticker,
                "price": quote.price,
                "volume": quote.volume,
                "timestamp": quote.timestamp.isoformat(),
                "source": quote.source,
                "bid": quote.bid,
                "ask": quote.ask,
                "open": quote.open,
                "high": quote.high,
                "low": quote.low,
                "previous_close": quote.previous_close
            }
        }
    
    async def publish_batch(self, quotes: List[Quote]) -> int:
        """Publish a batch of quotes to Redis.
        
        Wraps each quote in CloudEvents format and publishes to Redis channel.
        Uses circuit breaker to prevent cascading failures.
        
        Args:
            quotes: List of Quote objects to publish
            
        Returns:
            Number of quotes successfully published
            
        Raises:
            redis.RedisError: If Redis connection fails
        """
        if not quotes:
            return 0
        
        published_count = 0
        
        for quote in quotes:
            try:
                with REDIS_PUBLISH_LATENCY_SECONDS.time():
                    # Convert to CloudEvents format
                    event = self._quote_to_cloudevent(quote)
                    event_json = json.dumps(event)
                    
                    # Publish with circuit breaker
                    async def publish():
                        client = await self._get_client()
                        await client.publish(self.channel, event_json)
                    
                    await self._circuit_breaker.call(publish)
                    
                published_count += 1
                REDIS_PUBLISHES_TOTAL.labels(status="success").inc()
                
            except redis.RedisError as e:
                logger.error(f"Redis error publishing quote {quote.ticker}: {e}")
                REDIS_PUBLISH_ERRORS_TOTAL.labels(error_type="redis_error").inc()
                REDIS_PUBLISHES_TOTAL.labels(status="error").inc()
                # Continue with next quote (at-least-once delivery)
                
            except Exception as e:
                logger.error(f"Unexpected error publishing quote {quote.ticker}: {e}")
                REDIS_PUBLISH_ERRORS_TOTAL.labels(error_type="unknown").inc()
                REDIS_PUBLISHES_TOTAL.labels(status="error").inc()
        
        logger.info(f"Published {published_count}/{len(quotes)} quotes to Redis")
        return published_count
    
    async def close(self) -> None:
        """Close Redis connection.
        
        Should be called on shutdown to cleanly close the connection.
        """
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")
