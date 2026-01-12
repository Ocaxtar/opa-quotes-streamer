"""Unit tests for StoragePublisher."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
from datetime import datetime, timezone

from opa_quotes_streamer.publishers.storage_publisher import (
    StoragePublisher,
    PublisherError
)
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
            timestamp=datetime.now(timezone.utc),
            source="yfinance"
        ),
        Quote(
            ticker="MSFT",
            price=350.20,
            volume=89234000,
            timestamp=datetime.now(timezone.utc),
            source="yfinance"
        )
    ]


class TestStoragePublisher:
    """Test suite for StoragePublisher class."""
    
    def test_init_default_params(self):
        """Test initialization with default parameters."""
        publisher = StoragePublisher("http://localhost:8000")
        
        assert publisher.storage_url == "http://localhost:8000"
        assert publisher.timeout == 10
        assert publisher.circuit_breaker is not None
        assert publisher.circuit_breaker.failure_threshold == 5
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        publisher = StoragePublisher(
            "http://storage:9000",
            timeout=30,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=120
        )
        
        assert publisher.storage_url == "http://storage:9000"
        assert publisher.timeout == 30
        assert publisher.circuit_breaker.failure_threshold == 10
        assert publisher.circuit_breaker.timeout == 120
    
    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from URL."""
        publisher = StoragePublisher("http://localhost:8000/")
        
        assert publisher.storage_url == "http://localhost:8000"
    
    @pytest.mark.asyncio
    async def test_publish_batch_empty_list(self):
        """Test publish_batch with empty quotes list."""
        publisher = StoragePublisher("http://localhost:8000")
        
        result = await publisher.publish_batch([])
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_publish_batch_success(self, sample_quotes):
        """Test successful batch publishing."""
        publisher = StoragePublisher("http://localhost:8000")
        
        mock_response = Mock()
        mock_response.json.return_value = {"inserted": 2, "errors": 0}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await publisher.publish_batch(sample_quotes)
        
        assert result == 2
        mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_batch_partial_errors(self, sample_quotes):
        """Test publishing with partial errors."""
        publisher = StoragePublisher("http://localhost:8000")
        
        mock_response = Mock()
        mock_response.json.return_value = {"inserted": 1, "errors": 1}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await publisher.publish_batch(sample_quotes)
        
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_publish_batch_http_error(self, sample_quotes):
        """Test handling of HTTP errors."""
        publisher = StoragePublisher("http://localhost:8000")
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        http_error = httpx.HTTPStatusError(
            "500 Server Error",
            request=Mock(),
            response=mock_response
        )
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = http_error
            
            with pytest.raises(PublisherError, match="Storage publish failed"):
                await publisher.publish_batch(sample_quotes)
    
    @pytest.mark.asyncio
    async def test_publish_batch_network_error(self, sample_quotes):
        """Test handling of network errors."""
        publisher = StoragePublisher("http://localhost:8000")
        
        network_error = httpx.RequestError("Connection refused")
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = network_error
            
            with pytest.raises(PublisherError, match="Storage publish failed"):
                await publisher.publish_batch(sample_quotes)
    
    @pytest.mark.asyncio
    async def test_publish_batch_with_circuit_breaker(self, sample_quotes):
        """Test that circuit breaker is used."""
        publisher = StoragePublisher("http://localhost:8000")
        
        mock_response = Mock()
        mock_response.json.return_value = {"inserted": 2, "errors": 0}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post, \
             patch.object(publisher.circuit_breaker, 'call', new_callable=AsyncMock) as mock_circuit:
            
            mock_post.return_value = mock_response
            mock_circuit.return_value = {"inserted": 2, "errors": 0}
            
            await publisher.publish_batch(sample_quotes)
            
            mock_circuit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_batch_circuit_open(self, sample_quotes):
        """Test behavior when circuit breaker is OPEN."""
        publisher = StoragePublisher("http://localhost:8000")
        
        # Force circuit to OPEN state
        with patch.object(
            publisher.circuit_breaker,
            'call',
            side_effect=CircuitBreakerOpenError("Circuit is OPEN")
        ):
            with pytest.raises(PublisherError, match="circuit breaker OPEN"):
                await publisher.publish_batch(sample_quotes)
    
    @pytest.mark.asyncio
    async def test_publish_batch_triggers_circuit_open(self, sample_quotes):
        """Test that multiple failures open the circuit."""
        publisher = StoragePublisher(
            "http://localhost:8000",
            circuit_breaker_threshold=3
        )
        
        network_error = httpx.RequestError("Connection refused")
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = network_error
            
            # Fail 3 times to reach threshold
            for _ in range(3):
                with pytest.raises(PublisherError):
                    await publisher.publish_batch(sample_quotes)
            
            # Circuit should now be OPEN
            assert publisher.get_circuit_state() == "open"
    
    @pytest.mark.asyncio
    async def test_post_quotes_correct_payload(self, sample_quotes):
        """Test that _post_quotes sends correct payload format."""
        publisher = StoragePublisher("http://localhost:8000")
        
        mock_response = Mock()
        mock_response.json.return_value = {"inserted": 2, "errors": 0}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await publisher._post_quotes(sample_quotes)
            
            # Verify payload structure
            call_args = mock_post.call_args
            assert call_args[1]['json']['quotes'] is not None
            assert len(call_args[1]['json']['quotes']) == 2
            
            # Verify URL includes /v1 prefix
            assert call_args[0][0] == "http://localhost:8000/v1/quotes/batch"
    
    @pytest.mark.asyncio
    async def test_post_quotes_timeout_applied(self, sample_quotes):
        """Test that timeout is applied to HTTP client."""
        publisher = StoragePublisher("http://localhost:8000", timeout=30)
        
        mock_response = Mock()
        mock_response.json.return_value = {"inserted": 2, "errors": 0}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = mock_client_class.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            await publisher._post_quotes(sample_quotes)
            
            mock_client_class.assert_called_once_with(timeout=30)
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        publisher = StoragePublisher("http://localhost:8000")
        
        # Should not raise any exception
        await publisher.close()
    
    def test_get_circuit_state(self):
        """Test getting circuit breaker state."""
        publisher = StoragePublisher("http://localhost:8000")
        
        state = publisher.get_circuit_state()
        
        assert state == "closed"
    
    def test_reset_circuit(self):
        """Test manual circuit reset."""
        publisher = StoragePublisher("http://localhost:8000")
        
        # Force failures to open circuit
        for _ in range(5):
            publisher.circuit_breaker.failures += 1
        
        publisher.circuit_breaker.state = publisher.circuit_breaker.state.OPEN
        
        # Reset circuit
        publisher.reset_circuit()
        
        assert publisher.get_circuit_state() == "closed"
        assert publisher.circuit_breaker.get_failure_count() == 0
    
    @pytest.mark.asyncio
    async def test_publish_batch_logs_success(self, sample_quotes, caplog):
        """Test that successful publish logs appropriate messages."""
        import logging
        caplog.set_level(logging.INFO)
        
        publisher = StoragePublisher("http://localhost:8000")
        
        mock_response = Mock()
        mock_response.json.return_value = {"inserted": 2, "errors": 0}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await publisher.publish_batch(sample_quotes)
            
            # Check logs
            assert "Publishing batch of 2 quotes" in caplog.text
            assert "Batch published successfully" in caplog.text
    
    @pytest.mark.asyncio
    async def test_publish_batch_logs_errors(self, sample_quotes, caplog):
        """Test that failed publish logs errors."""
        import logging
        caplog.set_level(logging.ERROR)
        
        publisher = StoragePublisher("http://localhost:8000")
        
        network_error = httpx.RequestError("Connection refused")
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = network_error
            
            with pytest.raises(PublisherError):
                await publisher.publish_batch(sample_quotes)
            
            assert "Failed to publish batch" in caplog.text
    
    @pytest.mark.asyncio
    async def test_model_dump_serialization(self, sample_quotes):
        """Test that Quote.model_dump() is used for serialization."""
        publisher = StoragePublisher("http://localhost:8000")
        
        mock_response = Mock()
        mock_response.json.return_value = {"inserted": 2, "errors": 0}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await publisher._post_quotes(sample_quotes)
            
            # Verify that serialization happened
            call_args = mock_post.call_args
            quotes_data = call_args[1]['json']['quotes']
            
            # Check first quote structure
            assert 'ticker' in quotes_data[0]
            assert 'price' in quotes_data[0]
            assert 'volume' in quotes_data[0]
            assert 'timestamp' in quotes_data[0]
            assert 'source' in quotes_data[0]
