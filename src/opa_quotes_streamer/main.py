""" 
opa-quotes-streamer - Real-time streaming service
"""
import asyncio
import logging
import signal
import time
from typing import List

from opa_quotes_streamer.config import get_settings
from opa_quotes_streamer.logging_setup import setup_logging
from opa_quotes_streamer.sources.yfinance_source import YFinanceSource
from opa_quotes_streamer.publishers.storage_publisher import StoragePublisher, PublisherError
from opa_quotes_streamer.metrics import StreamingMetrics
from opa_shared_utils.utils.pipeline_logger import PipelineLogger

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


class StreamingService:
    """Real-time streaming service with polling loop."""
    
    def __init__(self):
        self.pipeline_logger = PipelineLogger(
            repository="opa-quotes-streamer",
            pipeline_name="quotes-streaming",
            db_url=settings.database_url
        )
        self.running = False
        
        # Parse tickers from settings
        self.tickers = [t.strip() for t in settings.tickers.split(",")]
        logger.info(f"Configured tickers: {self.tickers}")
        
        # Initialize components
        self.source = YFinanceSource(
            max_requests_per_hour=settings.max_requests_per_hour
        )
        self.publisher = StoragePublisher(
            storage_url=settings.storage_api_url,
            timeout=settings.storage_timeout,
            circuit_breaker_threshold=settings.circuit_breaker_threshold,
            circuit_breaker_timeout=settings.circuit_breaker_timeout
        )
        self.metrics = StreamingMetrics()
        
        # Counters
        self.total_quotes_fetched = 0
        self.total_quotes_published = 0
        self.cycle_count = 0
    
    async def start(self):
        """Start streaming service."""
        self.pipeline_logger.start(triggered_by="streamer-init")
        logger.info(f"Starting {settings.app_name} v{settings.version}")
        logger.info(f"Tickers: {settings.tickers}")
        logger.info(f"Polling interval: {settings.polling_interval}s")
        
        # Start metrics server
        self.metrics.start_metrics_server(port=settings.metrics_port)
        self.metrics.set_active_tickers(len(settings.tickers.split(",")))
        
        self.running = True
        
        try:
            await self.stream_loop()
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            self.metrics.record_error("critical")
            self.pipeline_logger.complete(
                status="failed",
                output_records=self.total_quotes_published,
                metadata={"error": str(e), "cycles": self.cycle_count}
            )
            raise
    
    async def stream_loop(self):
        """Main streaming loop with fetch + publish cycle."""
        logger.info("Entering streaming loop...")
        
        while self.running:
            cycle_start = time.time()
            
            try:
                # Fetch quotes
                fetch_start = time.time()
                quotes = await self.source.fetch_quotes(self.tickers)
                fetch_duration = time.time() - fetch_start
                
                if quotes:
                    self.total_quotes_fetched += len(quotes)
                    self.metrics.record_fetch(len(quotes), fetch_duration)
                    logger.info(f"Fetched {len(quotes)} quotes in {fetch_duration:.2f}s")
                    
                    # Publish to storage
                    publish_start = time.time()
                    try:
                        inserted = await self.publisher.publish_batch(quotes)
                        publish_duration = time.time() - publish_start
                        
                        self.total_quotes_published += inserted
                        self.metrics.record_publish(inserted, publish_duration)
                        logger.info(f"Published {inserted} quotes in {publish_duration:.2f}s")
                        
                        # Update circuit breaker state metric
                        cb_state = self.publisher.get_circuit_state()
                        self.metrics.set_circuit_breaker_state("storage", cb_state)
                        
                    except PublisherError as e:
                        logger.warning(f"Publisher error: {e}")
                        self.metrics.record_error("publish")
                        
                        # Update circuit breaker state even on error
                        cb_state = self.publisher.get_circuit_state()
                        self.metrics.set_circuit_breaker_state("storage", cb_state)
                else:
                    logger.debug("No quotes fetched this cycle")
                
                # Record full cycle duration
                cycle_duration = time.time() - cycle_start
                self.metrics.loop_duration_seconds.observe(cycle_duration)
                self.cycle_count += 1
                
                # Log cycle summary
                logger.info(
                    f"Cycle {self.cycle_count} completed in {cycle_duration:.2f}s "
                    f"(total fetched: {self.total_quotes_fetched}, "
                    f"total published: {self.total_quotes_published})"
                )
                
                # Polling interval sleep
                await asyncio.sleep(settings.polling_interval)
                
            except asyncio.CancelledError:
                logger.info("Stream cancelled, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in stream loop: {e}", exc_info=True)
                self.metrics.record_error("stream_loop")
                await asyncio.sleep(5)  # Backoff on error
        
        # Finalize
        self.pipeline_logger.complete(
            status="success",
            output_records=self.total_quotes_published,
            metadata={
                "cycles": self.cycle_count,
                "quotes_fetched": self.total_quotes_fetched,
                "quotes_published": self.total_quotes_published
            }
        )
        logger.info(f"Stream loop exited after {self.cycle_count} cycles")
    
    async def stop(self):
        """Stop streaming service gracefully."""
        logger.info("Stopping streaming service...")
        self.running = False
        
        # Close publisher connection
        await self.publisher.close()
        
        logger.info("Streaming service stopped")


async def main():
    """Main entry point with graceful shutdown."""
    service = StreamingService()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler(sig):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(service.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
