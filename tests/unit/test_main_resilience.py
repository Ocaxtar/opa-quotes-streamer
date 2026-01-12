"""
Unit tests for StreamingService resilience to PipelineLogger DB failures.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.exc import OperationalError

from opa_quotes_streamer.main import StreamingService


@pytest.mark.asyncio
async def test_streaming_service_starts_when_pipeline_logger_db_unavailable():
    """
    Test that StreamingService can start even when PipelineLogger 
    cannot connect to database (DB unavailable in integration environment).
    """
    with patch('opa_quotes_streamer.main.PipelineLogger') as mock_pipeline_logger_class:
        # Mock PipelineLogger.start() to raise OperationalError
        mock_logger_instance = Mock()
        mock_logger_instance.start.side_effect = OperationalError(
            "could not translate host name \"timescaledb\" to address",
            params=None,
            orig=None
        )
        mock_logger_instance.complete = Mock()
        mock_pipeline_logger_class.return_value = mock_logger_instance
        
        # Mock other components
        with patch('opa_quotes_streamer.main.YFinanceSource'), \
             patch('opa_quotes_streamer.main.StoragePublisher'), \
             patch('opa_quotes_streamer.main.StreamingMetrics') as mock_metrics:
            
            mock_metrics_instance = Mock()
            mock_metrics_instance.start_metrics_server = Mock()
            mock_metrics_instance.set_active_tickers = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Create service
            service = StreamingService()
            
            # Mock stream_loop to avoid actual streaming
            service.stream_loop = AsyncMock()
            
            # Start should NOT crash despite PipelineLogger.start() raising OperationalError
            await service.start()
            
            # Verify that stream_loop was called (service continued after fallback)
            service.stream_loop.assert_called_once()
            
            # Verify PipelineLogger.start() was called (but failed)
            mock_logger_instance.start.assert_called_once_with(triggered_by="streamer-init")


@pytest.mark.asyncio
async def test_streaming_service_completes_when_pipeline_logger_db_unavailable():
    """
    Test that StreamingService can complete gracefully even when 
    PipelineLogger.complete() fails due to DB unavailability.
    """
    with patch('opa_quotes_streamer.main.PipelineLogger') as mock_pipeline_logger_class:
        # Mock PipelineLogger
        mock_logger_instance = Mock()
        mock_logger_instance.start = Mock()  # start succeeds
        mock_logger_instance.complete.side_effect = OperationalError(
            "could not translate host name \"timescaledb\" to address",
            params=None,
            orig=None
        )
        mock_pipeline_logger_class.return_value = mock_logger_instance
        
        # Mock other components
        with patch('opa_quotes_streamer.main.YFinanceSource'), \
             patch('opa_quotes_streamer.main.StoragePublisher'), \
             patch('opa_quotes_streamer.main.StreamingMetrics'):
            
            # Create service
            service = StreamingService()
            service.running = False  # Don't actually run loop
            
            # stream_loop should complete WITHOUT crashing
            await service.stream_loop()
            
            # Verify PipelineLogger.complete() was called (but failed gracefully)
            mock_logger_instance.complete.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_service_handles_exception_with_db_unavailable():
    """
    Test that StreamingService handles exceptions in stream_loop 
    gracefully even when PipelineLogger.complete() fails.
    """
    with patch('opa_quotes_streamer.main.PipelineLogger') as mock_pipeline_logger_class:
        # Mock PipelineLogger with complete() failing
        mock_logger_instance = Mock()
        mock_logger_instance.start = Mock()
        mock_logger_instance.complete.side_effect = OperationalError(
            "DB unavailable",
            params=None,
            orig=None
        )
        mock_pipeline_logger_class.return_value = mock_logger_instance
        
        # Mock other components
        with patch('opa_quotes_streamer.main.YFinanceSource'), \
             patch('opa_quotes_streamer.main.StoragePublisher'), \
             patch('opa_quotes_streamer.main.StreamingMetrics') as mock_metrics:
            
            mock_metrics_instance = Mock()
            mock_metrics_instance.start_metrics_server = Mock()
            mock_metrics_instance.set_active_tickers = Mock()
            mock_metrics_instance.record_error = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Create service
            service = StreamingService()
            
            # Mock stream_loop to raise exception
            service.stream_loop = AsyncMock(side_effect=RuntimeError("Stream error"))
            
            # Start should handle exception and try to log completion (which fails)
            with pytest.raises(RuntimeError, match="Stream error"):
                await service.start()
            
            # Verify error was recorded
            mock_metrics_instance.record_error.assert_called_once_with("critical")
            
            # Verify PipelineLogger.complete() was called (despite failing)
            mock_logger_instance.complete.assert_called_once()
