"""Unit tests for RedisPublisher."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from datetime import datetime, timezone

from opa_quotes_streamer.publishers.redis_publisher import RedisPublisher
from opa_quotes_streamer.models.quote import Quote
from opa_quotes_streamer.utils.circuit_breaker import CircuitBreakerOpenError


@pytest.fixture
def sample_quotes():
    """Create sample quotes for testing."""
    return [
        Quote(
            ticker="AAPL",
            price=178.45,
            volume=52341000,
            timestamp=datetime(2025, 1, 19, 15, 30, 0, tzinfo=timezone.utc),
            source="yfinance",
            bid=178.44,
            ask=178.46,
            open=175.00,
            high=179.00,
            low=174.50,
            previous_close=176.00
        ),
        Quote(
            ticker="MSFT",
            price=350.20,
            volume=89234000,
            timestamp=datetime(2025, 1, 19, 15, 30, 0, tzinfo=timezone.utc),
            source="yfinance"
        )
    ]


class TestRedisPublisher:
    """Test suite for RedisPublisher class."""
    
    def test_init_default_params(self):
        """Test initialization with default parameters."""
        publisher = RedisPublisher()
        
        assert publisher.redis_url == "redis://localhost:6381"
        assert publisher.channel == "quotes.realtime"
        assert publisher._circuit_breaker is not None
        assert publisher._client is None
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        publisher = RedisPublisher(
            redis_url="redis://redis-server:6379",
            channel="custom-channel"
        )
        
        assert publisher.redis_url == "redis://redis-server:6379"
        assert publisher.channel == "custom-channel"
    
    @pytest.mark.asyncio
    async def test_publish_batch_empty_list(self):
        """Test publish_batch with empty quotes list."""
        publisher = RedisPublisher()
        
        result = await publisher.publish_batch([])
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_get_client_creates_connection(self):
        """Test that _get_client creates Redis connection."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        
        with patch('redis.asyncio.from_url', side_effect=mock_from_url) as mock_from_url_patch:
            client = await publisher._get_client()
            
            assert client == mock_redis
            mock_from_url_patch.assert_called_once_with(
                "redis://localhost:6381",
                encoding="utf-8",
                decode_responses=True
            )
            mock_redis.ping.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_get_client_reuses_connection(self):
        """Test that _get_client reuses existing connection."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        publisher._client = mock_redis
        
        with patch('redis.asyncio.from_url') as mock_from_url:
            client = await publisher._get_client()
            
            assert client == mock_redis
            mock_from_url.assert_not_called()  # Should not create new connection
    
    def test_quote_to_cloudevent_format(self, sample_quotes):
        """Test CloudEvents 1.0 format conversion."""
        publisher = RedisPublisher()
        quote = sample_quotes[0]
        
        with patch('opa_quotes_streamer.publishers.redis_publisher.uuid4') as mock_uuid, \
             patch('opa_quotes_streamer.publishers.redis_publisher.datetime') as mock_datetime:
            
            mock_uuid.return_value = "test-uuid-1234"
            mock_datetime.now.return_value = datetime(2025, 1, 19, 16, 0, 0, tzinfo=timezone.utc)
            
            event = publisher._quote_to_cloudevent(quote)
            
            # Validate CloudEvents 1.0 structure
            assert event["specversion"] == "1.0"
            assert event["type"] == "com.opamachine.quotes.price-updated"
            assert event["source"] == "opa-quotes-streamer"
            assert event["id"] == "test-uuid-1234"
            assert event["datacontenttype"] == "application/json"
            
            # Validate data payload
            assert event["data"]["ticker"] == "AAPL"
            assert event["data"]["price"] == 178.45
            assert event["data"]["volume"] == 52341000
            assert event["data"]["source"] == "yfinance"
            assert event["data"]["bid"] == 178.44
            assert event["data"]["ask"] == 178.46
            assert event["data"]["open"] == 175.00
            assert event["data"]["high"] == 179.00
            assert event["data"]["low"] == 174.50
            assert event["data"]["previous_close"] == 176.00
    
    def test_quote_to_cloudevent_optional_fields(self, sample_quotes):
        """Test CloudEvents format with optional null fields."""
        publisher = RedisPublisher()
        quote = sample_quotes[1]  # MSFT without optional fields
        
        event = publisher._quote_to_cloudevent(quote)
        
        # Optional fields should be None
        assert event["data"]["bid"] is None
        assert event["data"]["ask"] is None
        assert event["data"]["open"] is None
        assert event["data"]["high"] is None
        assert event["data"]["low"] is None
        assert event["data"]["previous_close"] is None
    
    @pytest.mark.asyncio
    async def test_publish_batch_success(self, sample_quotes):
        """Test successful batch publishing to Redis."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)  # 1 subscriber
        
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        
        with patch('redis.asyncio.from_url', side_effect=mock_from_url):
            result = await publisher.publish_batch(sample_quotes)
        
        assert result == 2  # Both quotes published
        assert mock_redis.publish.call_count == 2
        
        # Verify published data format
        first_call = mock_redis.publish.call_args_list[0]
        channel, payload = first_call[0]
        
        assert channel == "quotes.realtime"
        
        event = json.loads(payload)
        assert event["specversion"] == "1.0"
        assert event["type"] == "com.opamachine.quotes.price-updated"
        assert event["data"]["ticker"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_publish_batch_redis_error(self, sample_quotes):
        """Test publishing with Redis connection error."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.publish = AsyncMock(side_effect=Exception("Connection refused"))
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            result = await publisher.publish_batch(sample_quotes)
        
        # Should handle error gracefully and continue
        assert result == 0  # No quotes published due to error
    
    @pytest.mark.asyncio
    async def test_publish_batch_partial_failure(self, sample_quotes):
        """Test publishing with partial failures."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        
        # First publish fails, second succeeds
        mock_redis.publish = AsyncMock(side_effect=[
            Exception("Temporary error"),
            1  # Success
        ])
        
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        
        with patch('redis.asyncio.from_url', side_effect=mock_from_url):
            result = await publisher.publish_batch(sample_quotes)
        
        assert result == 1  # Only second quote published
    
    @pytest.mark.asyncio
    async def test_publish_batch_circuit_breaker_open(self, sample_quotes):
        """Test publishing when circuit breaker is open."""
        publisher = RedisPublisher()
        
        # Simulate open circuit
        publisher._circuit_breaker.state = "open"
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        publisher._client = mock_redis
        
        # Circuit breaker should prevent calls
        with patch.object(publisher._circuit_breaker, 'call', side_effect=CircuitBreakerOpenError("Circuit open")):
            result = await publisher.publish_batch(sample_quotes)
        
        assert result == 0  # No quotes published
    
    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test closing Redis connection."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        publisher._client = mock_redis
        
        await publisher.close()
        
        mock_redis.close.assert_awaited_once()
        assert publisher._client is None
    
    @pytest.mark.asyncio
    async def test_close_no_connection(self):
        """Test closing when no connection exists."""
        publisher = RedisPublisher()
        
        # Should not raise error
        await publisher.close()
        
        assert publisher._client is None
    
    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(self, sample_quotes):
        """Test that Prometheus metrics are recorded on success."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)
        
        with patch('redis.asyncio.from_url', return_value=mock_redis), \
             patch('opa_quotes_streamer.publishers.redis_publisher.REDIS_PUBLISHES_TOTAL') as mock_counter, \
             patch('opa_quotes_streamer.publishers.redis_publisher.REDIS_PUBLISH_LATENCY_SECONDS') as mock_histogram:
            
            await publisher.publish_batch(sample_quotes)
            
            # Verify metrics were called
            assert mock_counter.labels.called
            assert mock_histogram.time.called
    
    @pytest.mark.asyncio
    async def test_metrics_recorded_on_error(self, sample_quotes):
        """Test that error metrics are recorded on failure."""
        publisher = RedisPublisher()
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.publish = AsyncMock(side_effect=Exception("Connection error"))
        
        with patch('redis.asyncio.from_url', return_value=mock_redis), \
             patch('opa_quotes_streamer.publishers.redis_publisher.REDIS_PUBLISH_ERRORS_TOTAL') as mock_error_counter:
            
            await publisher.publish_batch(sample_quotes)
            
            # Verify error metric was incremented
            assert mock_error_counter.labels.called
