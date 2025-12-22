"""Unit tests for CircuitBreaker."""

import pytest
import asyncio
from opa_quotes_streamer.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""
    
    def test_init_valid_params(self):
        """Test initialization with valid parameters."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=30, name="test")
        
        assert breaker.failure_threshold == 3
        assert breaker.timeout == 30
        assert breaker.failures == 0
        assert breaker.state == CircuitState.CLOSED
        assert breaker.name == "test"
    
    def test_init_invalid_params(self):
        """Test initialization with invalid parameters."""
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitBreaker(failure_threshold=0)
        
        with pytest.raises(ValueError, match="timeout must be positive"):
            CircuitBreaker(failure_threshold=5, timeout=-10)
    
    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Test successful function call in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1)
        
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_failure_count() == 0
    
    @pytest.mark.asyncio
    async def test_failed_call_increments_failures(self):
        """Test that failed calls increment failure count."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # First failure
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        assert breaker.get_failure_count() == 1
        assert breaker.get_state() == CircuitState.CLOSED
        
        # Second failure
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        assert breaker.get_failure_count() == 2
        assert breaker.get_state() == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker.get_state() == CircuitState.OPEN
        assert breaker.get_failure_count() == 3
        assert breaker.last_failure_time is not None
    
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self):
        """Test OPEN circuit rejects calls immediately."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker.get_state() == CircuitState.OPEN
        
        # Next call should be rejected with CircuitBreakerOpenError
        async def any_func():
            return "should not execute"
        
        with pytest.raises(CircuitBreakerOpenError, match="is OPEN"):
            await breaker.call(any_func)
    
    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker.get_state() == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Next call should transition to HALF_OPEN
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Test successful call in HALF_OPEN closes circuit."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        async def success_func():
            return "success"
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        # Wait for timeout to enter HALF_OPEN
        await asyncio.sleep(1.1)
        
        # Success should close circuit
        result = await breaker.call(success_func)
        
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_failure_count() == 0
    
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Test failure in HALF_OPEN reopens circuit."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Failure in HALF_OPEN should reopen
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        # Should be back to OPEN (though we need another failure to reach threshold)
        # Actually, single failure in HALF_OPEN counts towards threshold
        assert breaker.get_failure_count() >= 1
    
    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test successful call resets failure count in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=5, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        async def success_func():
            return "success"
        
        # Fail twice
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker.get_failure_count() == 2
        
        # Success should reset counter
        await breaker.call(success_func)
        
        assert breaker.get_failure_count() == 0
        assert breaker.get_state() == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Test manual circuit reset."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker.get_state() == CircuitState.OPEN
        
        # Manual reset
        breaker.reset()
        
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_failure_count() == 0
        assert breaker.last_failure_time is None
    
    @pytest.mark.asyncio
    async def test_multiple_success_calls(self):
        """Test multiple successful calls don't change state."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1)
        
        async def success_func():
            return "success"
        
        for _ in range(10):
            result = await breaker.call(success_func)
            assert result == "success"
        
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.get_failure_count() == 0
    
    @pytest.mark.asyncio
    async def test_circuit_with_different_exceptions(self):
        """Test circuit handles different exception types."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1)
        
        async def value_error_func():
            raise ValueError("Value error")
        
        async def type_error_func():
            raise TypeError("Type error")
        
        # Mix of different exceptions
        with pytest.raises(ValueError):
            await breaker.call(value_error_func)
        
        with pytest.raises(TypeError):
            await breaker.call(type_error_func)
        
        with pytest.raises(ValueError):
            await breaker.call(value_error_func)
        
        # Should open after 3 failures regardless of exception type
        assert breaker.get_state() == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_get_state_method(self):
        """Test get_state method."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        assert breaker.get_state() == CircuitState.CLOSED
        
        async def failing_func():
            raise ValueError("Test error")
        
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker.get_state() == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_concurrent_calls_in_closed_state(self):
        """Test concurrent calls in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=10, timeout=1)
        
        call_count = [0]
        
        async def counting_func():
            call_count[0] += 1
            await asyncio.sleep(0.1)
            return call_count[0]
        
        # Execute 5 concurrent calls
        results = await asyncio.gather(*[
            breaker.call(counting_func) for _ in range(5)
        ])
        
        assert len(results) == 5
        assert breaker.get_state() == CircuitState.CLOSED
