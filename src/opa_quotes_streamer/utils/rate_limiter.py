"""Token bucket rate limiter implementation."""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for API request throttling.
    
    This implementation uses the token bucket algorithm to limit requests per hour.
    Tokens are automatically refilled based on elapsed time.
    
    Attributes:
        capacity: Maximum number of tokens (requests) that can be stored
        tokens: Current number of available tokens
        refill_rate: Tokens refilled per second
        last_refill: Timestamp of last token refill
        lock: Async lock for thread-safe token operations
    
    Example:
        >>> limiter = RateLimiter(max_requests_per_hour=2000)
        >>> await limiter.acquire()  # Acquire one token
        >>> # Make API request here
    """
    
    def __init__(self, max_requests_per_hour: int):
        """Initialize rate limiter.
        
        Args:
            max_requests_per_hour: Maximum requests allowed per hour
        """
        if max_requests_per_hour <= 0:
            raise ValueError("max_requests_per_hour must be positive")
            
        self.capacity = max_requests_per_hour
        self.tokens = float(max_requests_per_hour)
        self.refill_rate = max_requests_per_hour / 3600.0  # Tokens per second
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire a token, waiting if none available.
        
        Args:
            timeout: Maximum time to wait for a token (seconds). None = infinite wait
            
        Returns:
            True if token acquired, False if timeout occurred
            
        Raises:
            asyncio.TimeoutError: If timeout is reached before acquiring token
        """
        start_time = time.time()
        
        async with self.lock:
            await self._refill()
            
            while self.tokens < 1:
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                
                await asyncio.sleep(0.1)
                await self._refill()
            
            self.tokens -= 1
            return True
    
    async def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now
    
    def available_tokens(self) -> float:
        """Get current number of available tokens without refilling.
        
        Returns:
            Current token count
        """
        return self.tokens
    
    async def wait_time(self) -> float:
        """Calculate approximate wait time until next token is available.
        
        Returns:
            Wait time in seconds (0 if tokens available)
        """
        async with self.lock:
            await self._refill()
            
            if self.tokens >= 1:
                return 0.0
            
            tokens_needed = 1 - self.tokens
            return tokens_needed / self.refill_rate
