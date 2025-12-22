"""Quote data model."""

from datetime import datetime
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
    def ticker_uppercase(cls, v: str) -> str:
        """Convert ticker to uppercase."""
        return v.upper().strip()
    
    @field_validator('source')
    @classmethod
    def source_lowercase(cls, v: str) -> str:
        """Convert source to lowercase."""
        return v.lower().strip()
    
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
