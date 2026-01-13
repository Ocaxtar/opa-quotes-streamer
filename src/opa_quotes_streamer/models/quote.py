"""Quote data model."""

import re
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Quote(BaseModel):
    """Real-time quote data model.
    
    Represents a single market quote with price, volume, and metadata.
    Validated using Pydantic for type safety and data integrity.
    
    Attributes:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        price: Current price in USD
        volume: Trading volume
        timestamp: Quote timestamp (UTC)
        source: Data source identifier (e.g., "yfinance", "iexcloud")
        bid: Optional bid price
        ask: Optional ask price
        open: Optional opening price
        high: Optional daily high
        low: Optional daily low
        previous_close: Optional previous closing price
    """
    
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Stock ticker symbol"
    )
    price: float = Field(
        ...,
        gt=0,
        description="Current price in USD"
    )
    volume: int = Field(
        ...,
        ge=0,
        description="Trading volume"
    )
    timestamp: datetime = Field(
        ...,
        description="Quote timestamp (UTC)"
    )
    source: str = Field(
        ...,
        min_length=1,
        description="Data source identifier"
    )
    
    # Optional fields
    bid: Optional[float] = Field(None, gt=0, description="Bid price")
    ask: Optional[float] = Field(None, gt=0, description="Ask price")
    open: Optional[float] = Field(None, gt=0, description="Opening price")
    high: Optional[float] = Field(None, gt=0, description="Daily high")
    low: Optional[float] = Field(None, gt=0, description="Daily low")
    previous_close: Optional[float] = Field(None, gt=0, description="Previous close")
    
    @field_validator('ticker')
    @classmethod
    def validate_ticker_format(cls, v: str) -> str:
        """Validate ticker format and convert to uppercase (INV-002).
        
        Contract invariant INV-002: Ticker must match ^[A-Z]{1,5}$
        """
        v = v.upper().strip()
        if not re.match(r'^[A-Z]{1,5}$', v):
            raise ValueError(
                f"Invalid ticker format: {v}. Must match ^[A-Z]{{1,5}}$ (INV-002)"
            )
        return v
    
    @field_validator('timestamp')
    @classmethod
    def validate_utc_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is in UTC timezone (INV-003).
        
        Contract invariant INV-003: Timestamp must be ISO 8601 UTC.
        """
        if v.tzinfo is None:
            raise ValueError(
                "Timestamp must have timezone info. Use datetime.now(timezone.utc) (INV-003)"
            )
        if v.tzinfo != timezone.utc:
            raise ValueError(
                f"Timestamp must be UTC, got {v.tzinfo}. Convert to UTC before creating Quote (INV-003)"
            )
        return v
    
    @field_validator('source')
    @classmethod
    def validate_source_enum(cls, v: str) -> str:
        """Validate source is one of allowed values and convert to lowercase (INV-005).
        
        Contract invariant INV-005: Source must be 'yfinance', 'fmp', or 'manual'.
        """
        v = v.lower().strip()
        valid_sources = ["yfinance", "fmp", "manual"]
        if v not in valid_sources:
            raise ValueError(
                f"Invalid source: {v}. Must be one of {valid_sources} (INV-005)"
            )
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "price": 178.45,
                "volume": 52341000,
                "timestamp": "2025-12-22T15:30:00Z",
                "source": "yfinance",
                "bid": 178.40,
                "ask": 178.50,
                "open": 175.20,
                "high": 179.00,
                "low": 174.50,
                "previous_close": 177.80
            }
        }
    )
