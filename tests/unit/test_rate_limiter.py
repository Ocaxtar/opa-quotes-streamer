"""Unit tests for RateLimiter."""

import pytest
import asyncio
import time
from opa_quotes_streamer.utils.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test suite for RateLimiter class."""
    
    def test_init_valid_params(self):
        """Test initialization with valid parameters."""
        limiter = RateLimiter(max_requests_per_hour=100)
        
        assert limiter.capacity == 100
        assert limiter.tokens == 100.0
        assert limiter.refill_rate == pytest.approx(100 / 3600, rel=1e-6)
        assert limiter.last_refill > 0
    
    def test_init_invalid_params(self):
        """Test initialization with invalid parameters."""
        with pytest.raises(ValueError, match="must be positive"):
            RateLimiter(max_requests_per_hour=0)
        
        with pytest.raises(ValueError, match="must be positive"):
            RateLimiter(max_requests_per_hour=-10)
    
    @pytest.mark.asyncio
    async def test_acquire_single_token(self):
        """Test acquiring a single token."""
        limiter = RateLimiter(max_requests_per_hour=100)
        
        # Should acquire immediately
        result = await limiter.acquire()
        
        assert result is True
        assert limiter.tokens == pytest.approx(99.0, rel=1e-1)
    
    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens sequentially."""
        limiter = RateLimiter(max_requests_per_hour=100)
        
        # Acquire 5 tokens
        for _ in range(5):
            result = await limiter.acquire()
            assert result is True
        
        assert limiter.tokens == pytest.approx(95.0, rel=1e-1)
    
    @pytest.mark.asyncio
    async def test_acquire_wait_for_refill(self):
        """Test waiting for token refill."""
        limiter = RateLimiter(max_requests_per_hour=3600)  # 1 token/second
        
        # Exhaust tokens
        limiter.tokens = 0.5
        
        start = time.time()
        result = await limiter.acquire()
        elapsed = time.time() - start
        
        assert result is True
        # Should wait ~0.5 seconds for refill
        assert 0.4 <= elapsed <= 0.7
    
    @pytest.mark.asyncio
    async def test_acquire_with_timeout(self):
        """Test acquire with timeout."""
        limiter = RateLimiter(max_requests_per_hour=3600)
        
        # Exhaust all tokens
        limiter.tokens = 0.0
        
        # Try to acquire with short timeout (should fail)
        result = await limiter.acquire(timeout=0.1)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_refill_over_time(self):
        """Test automatic token refilling."""
        limiter = RateLimiter(max_requests_per_hour=3600)  # 1 token/second
        
        # Start with 50 tokens
        limiter.tokens = 50.0
        
        # Wait 2 seconds
        await asyncio.sleep(2.0)
        
        # Trigger refill by checking available tokens
        await limiter._refill()
        
        # Should have ~52 tokens now (50 + 2)
        assert 51.5 <= limiter.tokens <= 52.5
    
    @pytest.mark.asyncio
    async def test_refill_does_not_exceed_capacity(self):
        """Test that refill doesn't exceed capacity."""
        limiter = RateLimiter(max_requests_per_hour=100)
        
        # Start at capacity
        limiter.tokens = 100.0
        
        # Wait and refill
        await asyncio.sleep(0.5)
        await limiter._refill()
        
        # Should still be at capacity
        assert limiter.tokens <= 100.0
    
    @pytest.mark.asyncio
    async def test_available_tokens(self):
        """Test getting available tokens count."""
        limiter = RateLimiter(max_requests_per_hour=100)
        
        assert limiter.available_tokens() == pytest.approx(100.0, rel=1e-1)
        
        await limiter.acquire()
        
        assert limiter.available_tokens() == pytest.approx(99.0, rel=1e-1)
    
    @pytest.mark.asyncio
    async def test_wait_time_with_tokens(self):
        """Test wait_time when tokens are available."""
        limiter = RateLimiter(max_requests_per_hour=100)
        
        wait = await limiter.wait_time()
        
        assert wait == 0.0
    
    @pytest.mark.asyncio
    async def test_wait_time_without_tokens(self):
        """Test wait_time when no tokens available."""
        limiter = RateLimiter(max_requests_per_hour=3600)  # 1 token/second
        
        # Exhaust tokens
        limiter.tokens = 0.0
        
        wait = await limiter.wait_time()
        
        # Should wait ~1 second for next token
        assert 0.9 <= wait <= 1.1
    
    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """Test concurrent token acquisition."""
        limiter = RateLimiter(max_requests_per_hour=1000)
        
        async def acquire_token():
            return await limiter.acquire()
        
        # Acquire 10 tokens concurrently
        results = await asyncio.gather(*[acquire_token() for _ in range(10)])
        
        # All should succeed
        assert all(results)
        
        # Should have consumed 10 tokens
        assert limiter.tokens == pytest.approx(990.0, rel=1e-1)
    
    @pytest.mark.asyncio
    async def test_high_frequency_requests(self):
        """Test rate limiting with high frequency requests."""
        limiter = RateLimiter(max_requests_per_hour=10)  # Very low limit
        
        # Consume all tokens
        for _ in range(10):
            await limiter.acquire()
        
        # Next acquire should wait
        limiter.tokens = 0.0
        start = time.time()
        result = await limiter.acquire(timeout=0.5)
        elapsed = time.time() - start
        
        # Should timeout before getting token
        assert result is False
        assert elapsed >= 0.5
