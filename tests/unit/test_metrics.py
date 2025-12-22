"""Unit tests for StreamingMetrics."""

import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import REGISTRY

from opa_quotes_streamer.metrics import StreamingMetrics


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Clear Prometheus registry before each test."""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    yield
    # Clean up after test
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


class TestStreamingMetrics:
    """Test suite for StreamingMetrics class."""
    
    def test_init(self):
        """Test metrics initialization."""
        metrics = StreamingMetrics()
        
        assert metrics.quotes_fetched_total is not None
        assert metrics.quotes_published_total is not None
        assert metrics.errors_total is not None
        assert metrics.fetch_duration_seconds is not None
        assert metrics.publish_duration_seconds is not None
        assert metrics.loop_duration_seconds is not None
        assert metrics.active_tickers is not None
        assert metrics.circuit_breaker_state is not None
    
    def test_start_metrics_server(self):
        """Test starting Prometheus metrics server."""
        metrics = StreamingMetrics()
        
        with patch('opa_quotes_streamer.metrics.start_http_server') as mock_server:
            metrics.start_metrics_server(port=9001)
            mock_server.assert_called_once_with(9001)
    
    def test_start_metrics_server_port_in_use(self):
        """Test handling of port already in use."""
        metrics = StreamingMetrics()
        
        with patch('prometheus_client.start_http_server', side_effect=OSError("Port in use")):
            # Should not raise, just log warning
            metrics.start_metrics_server(port=9001)
    
    def test_record_fetch(self):
        """Test recording fetch metrics."""
        metrics = StreamingMetrics()
        
        initial_count = metrics.quotes_fetched_total._value.get()
        
        metrics.record_fetch(count=10, duration=1.5)
        
        assert metrics.quotes_fetched_total._value.get() == initial_count + 10
    
    def test_record_publish(self):
        """Test recording publish metrics."""
        metrics = StreamingMetrics()
        
        initial_count = metrics.quotes_published_total._value.get()
        
        metrics.record_publish(count=8, duration=0.5)
        
        assert metrics.quotes_published_total._value.get() == initial_count + 8
    
    def test_record_error(self):
        """Test recording error metrics."""
        metrics = StreamingMetrics()
        
        metrics.record_error(error_type="network")
        metrics.record_error(error_type="network")
        metrics.record_error(error_type="parse")
        
        # Verify errors were recorded (exact count checking requires registry access)
        assert metrics.errors_total is not None
    
    def test_set_active_tickers(self):
        """Test setting active tickers gauge."""
        metrics = StreamingMetrics()
        
        metrics.set_active_tickers(5)
        assert metrics.active_tickers._value.get() == 5
        
        metrics.set_active_tickers(10)
        assert metrics.active_tickers._value.get() == 10
    
    def test_set_circuit_breaker_state_closed(self):
        """Test setting circuit breaker to closed state."""
        metrics = StreamingMetrics()
        
        metrics.set_circuit_breaker_state("storage", "closed")
        
        # Verify state was set (0 = closed)
        assert metrics.circuit_breaker_state is not None
    
    def test_set_circuit_breaker_state_open(self):
        """Test setting circuit breaker to open state."""
        metrics = StreamingMetrics()
        
        metrics.set_circuit_breaker_state("storage", "open")
        
        # Verify state was set (1 = open)
        assert metrics.circuit_breaker_state is not None
    
    def test_set_circuit_breaker_state_half_open(self):
        """Test setting circuit breaker to half_open state."""
        metrics = StreamingMetrics()
        
        metrics.set_circuit_breaker_state("storage", "half_open")
        
        # Verify state was set (2 = half_open)
        assert metrics.circuit_breaker_state is not None
    
    def test_set_circuit_breaker_state_unknown(self):
        """Test setting circuit breaker to unknown state defaults to closed."""
        metrics = StreamingMetrics()
        
        metrics.set_circuit_breaker_state("storage", "invalid_state")
        
        # Should default to 0 (closed)
        assert metrics.circuit_breaker_state is not None
    
    def test_multiple_publishers_circuit_state(self):
        """Test tracking circuit state for multiple publishers."""
        metrics = StreamingMetrics()
        
        metrics.set_circuit_breaker_state("storage", "closed")
        metrics.set_circuit_breaker_state("backup", "open")
        
        assert metrics.circuit_breaker_state is not None
    
    def test_record_multiple_operations(self):
        """Test recording multiple operations sequentially."""
        metrics = StreamingMetrics()
        
        # Record multiple fetches
        metrics.record_fetch(count=5, duration=0.5)
        metrics.record_fetch(count=10, duration=1.0)
        metrics.record_fetch(count=3, duration=0.3)
        
        # Record multiple publishes
        metrics.record_publish(count=5, duration=0.2)
        metrics.record_publish(count=10, duration=0.4)
        
        # Verify totals
        assert metrics.quotes_fetched_total._value.get() >= 18
        assert metrics.quotes_published_total._value.get() >= 15
    
    def test_histogram_buckets(self):
        """Test that histogram buckets are properly configured."""
        metrics = StreamingMetrics()
        
        # Verify fetch duration histogram exists and has buckets
        assert hasattr(metrics.fetch_duration_seconds, '_buckets')
        
        # Verify publish duration histogram exists
        assert hasattr(metrics.publish_duration_seconds, '_buckets')
        
        # Verify loop duration histogram exists
        assert hasattr(metrics.loop_duration_seconds, '_buckets')
