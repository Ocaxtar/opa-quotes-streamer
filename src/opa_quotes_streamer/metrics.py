"""Prometheus metrics for streaming service."""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)


class StreamingMetrics:
    """Prometheus metrics collector for streaming service."""
    
    def __init__(self):
        """Initialize all Prometheus metrics."""
        # Counters
        self.quotes_fetched_total = Counter(
            'streamer_quotes_fetched_total',
            'Total number of quotes successfully fetched'
        )
        
        self.quotes_published_total = Counter(
            'streamer_quotes_published_total',
            'Total number of quotes successfully published to storage'
        )
        
        self.errors_total = Counter(
            'streamer_errors_total',
            'Total number of errors by type',
            ['error_type']
        )
        
        # Histograms (for latency/duration)
        self.fetch_duration_seconds = Histogram(
            'streamer_fetch_duration_seconds',
            'Duration of quote fetch operations in seconds',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
        )
        
        self.publish_duration_seconds = Histogram(
            'streamer_publish_duration_seconds',
            'Duration of quote publish operations in seconds',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
        )
        
        self.loop_duration_seconds = Histogram(
            'streamer_loop_duration_seconds',
            'Duration of full streaming loop cycle in seconds',
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0)
        )
        
        # Gauges (for current state)
        self.active_tickers = Gauge(
            'streamer_active_tickers',
            'Number of tickers currently being tracked'
        )
        
        self.circuit_breaker_state = Gauge(
            'streamer_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half_open)',
            ['publisher']
        )
        
        logger.info("Prometheus metrics initialized")
    
    def start_metrics_server(self, port: int = 8001):
        """Start Prometheus HTTP server on specified port.
        
        Args:
            port: Port to expose metrics endpoint (default 8001)
        """
        try:
            start_http_server(port)
            logger.info(f"Metrics server started on port {port}")
        except OSError as e:
            logger.warning(f"Metrics server port {port} already in use: {e}")
    
    def record_fetch(self, count: int, duration: float):
        """Record successful fetch operation.
        
        Args:
            count: Number of quotes fetched
            duration: Time taken in seconds
        """
        self.quotes_fetched_total.inc(count)
        self.fetch_duration_seconds.observe(duration)
    
    def record_publish(self, count: int, duration: float):
        """Record successful publish operation.
        
        Args:
            count: Number of quotes published
            duration: Time taken in seconds
        """
        self.quotes_published_total.inc(count)
        self.publish_duration_seconds.observe(duration)
    
    def record_error(self, error_type: str):
        """Record an error occurrence.
        
        Args:
            error_type: Type of error (e.g., 'fetch', 'publish', 'network')
        """
        self.errors_total.labels(error_type=error_type).inc()
    
    def set_active_tickers(self, count: int):
        """Update the number of active tickers.
        
        Args:
            count: Current number of tickers being tracked
        """
        self.active_tickers.set(count)
    
    def set_circuit_breaker_state(self, publisher: str, state: str):
        """Update circuit breaker state.
        
        Args:
            publisher: Name of the publisher
            state: Current state ('closed', 'open', 'half_open')
        """
        state_map = {
            'closed': 0,
            'open': 1,
            'half_open': 2
        }
        self.circuit_breaker_state.labels(publisher=publisher).set(
            state_map.get(state.lower(), 0)
        )
