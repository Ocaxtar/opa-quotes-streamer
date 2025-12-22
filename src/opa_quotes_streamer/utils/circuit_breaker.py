"""Circuit breaker pattern implementation for fault tolerance."""

import time
from enum import Enum
from typing import Callable, Any, Optional, TypeVar, Awaitable
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker for resilient service calls.
    
    Implements the circuit breaker pattern to prevent cascading failures.
    The circuit transitions between three states:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Service is failing, requests are immediately rejected
    - HALF_OPEN: Testing recovery, limited requests allowed
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds to wait before transitioning from OPEN to HALF_OPEN
        failures: Current failure count
        last_failure_time: Timestamp of last failure
        state: Current circuit state
    
    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>> async def fetch_data():
        ...     # Make API call
        ...     return data
        >>> result = await breaker.call(fetch_data)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        name: Optional[str] = None
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            timeout: Seconds to wait in OPEN state before trying HALF_OPEN
            name: Optional name for logging purposes
        """
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
            
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.name = name or "unnamed"
        self._success_count_half_open = 0
    
    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            
        Returns:
            Result of func() execution
            
        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: Original exception from func() if circuit is CLOSED/HALF_OPEN
        """
        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and \
               time.time() - self.last_failure_time >= self.timeout:
                logger.info(
                    f"Circuit breaker '{self.name}' transitioning to HALF_OPEN "
                    f"after {self.timeout}s timeout"
                )
                self.state = CircuitState.HALF_OPEN
                self._success_count_half_open = 0
            else:
                logger.warning(
                    f"Circuit breaker '{self.name}' is OPEN, rejecting call"
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
        
        try:
            # Execute the function
            result = await func()
            
            # On success in HALF_OPEN, transition to CLOSED
            if self.state == CircuitState.HALF_OPEN:
                self._success_count_half_open += 1
                logger.info(
                    f"Circuit breaker '{self.name}' successful call in HALF_OPEN "
                    f"(success count: {self._success_count_half_open})"
                )
                
                # After first success in HALF_OPEN, close the circuit
                self.state = CircuitState.CLOSED
                self.failures = 0
                logger.info(
                    f"Circuit breaker '{self.name}' transitioned to CLOSED"
                )
            
            # Reset failure count on success in CLOSED state
            if self.state == CircuitState.CLOSED:
                self.failures = 0
            
            return result
            
        except Exception as e:
            # Increment failure count
            self.failures += 1
            logger.error(
                f"Circuit breaker '{self.name}' call failed "
                f"(failures: {self.failures}/{self.failure_threshold}): {e}"
            )
            
            # Open circuit if threshold exceeded
            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_failure_time = time.time()
                logger.error(
                    f"Circuit breaker '{self.name}' opened after "
                    f"{self.failures} failures"
                )
            
            raise
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = None
        self._success_count_half_open = 0
    
    def get_state(self) -> CircuitState:
        """Get current circuit state.
        
        Returns:
            Current CircuitState
        """
        return self.state
    
    def get_failure_count(self) -> int:
        """Get current failure count.
        
        Returns:
            Number of consecutive failures
        """
        return self.failures
