"""Configuration management using Pydantic Settings."""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import yaml


def load_tickers_from_yaml() -> str:
    """Load tickers from YAML config file if TICKERS env var not set.
    
    Returns:
        Comma-separated string of tickers
    """
    # If TICKERS is explicitly set, use it
    if os.getenv("TICKERS"):
        return os.getenv("TICKERS")
    
    # Try to load from config file
    config_file = Path("/app/config/streaming-300.yaml")
    if not config_file.exists():
        config_file = Path(__file__).parent.parent.parent / "config" / "streaming-300.yaml"
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            tickers = config.get('sources', {}).get('yahoo_finance', {}).get('tickers', [])
            if tickers:
                return ','.join(tickers)
    
    # Fallback to default
    return "AAPL,MSFT,GOOGL,AMZN,TSLA"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Attributes:
        app_name: Application name
        version: Application version
        environment: Runtime environment (dev, staging, prod)
        tickers: List of ticker symbols to stream
        polling_interval: Seconds between polling cycles
        max_requests_per_hour: Rate limit for API requests
        storage_api_url: URL of opa-quotes-storage service
        storage_timeout: HTTP timeout for storage requests (seconds)
        circuit_breaker_threshold: Failures before circuit opens
        circuit_breaker_timeout: Seconds before circuit half-opens
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        prometheus_port: Port for Prometheus metrics endpoint
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application
    app_name: str = "opa-quotes-streamer"
    version: str = "0.1.0"
    environment: str = Field(default="dev", pattern="^(dev|staging|prod|integration)$")
    
    # Streaming configuration
    tickers: str = Field(
        default_factory=load_tickers_from_yaml,
        description="Comma-separated tickers to stream (loaded from YAML if not set)"
    )
    polling_interval: int = Field(
        default=5,
        ge=1,
        le=300,
        description="Seconds between polls"
    )
    
    # Rate limiting
    max_requests_per_hour: int = Field(
        default=2000,
        ge=1,
        description="Maximum API requests per hour"
    )
    
    # Storage integration
    storage_api_url: str = Field(
        default="http://localhost:8000",
        description="opa-quotes-storage URL"
    )
    storage_timeout: int = Field(
        default=30,
        ge=1,
        description="Storage request timeout (seconds)"
    )
    publisher_enabled: bool = Field(
        default=True,
        description="Enable/disable storage publisher"
    )
    
    # Redis Pub/Sub configuration
    redis_url: str = Field(
        default="redis://localhost:6381",
        description="Redis connection URL for Pub/Sub"
    )
    redis_channel: str = Field(
        default="quotes.realtime",
        description="Redis channel for quote events"
    )
    redis_publisher_enabled: bool = Field(
        default=True,
        description="Enable/disable Redis publisher"
    )
    
    # Circuit breaker
    circuit_breaker_threshold: int = Field(
        default=5,
        ge=1,
        description="Failures before opening circuit"
    )
    circuit_breaker_timeout: int = Field(
        default=60,
        ge=1,
        description="Seconds before half-open attempt"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    
    # Metrics
    metrics_port: int = Field(
        default=8001,
        ge=1024,
        le=65535,
        description="Prometheus metrics port"
    )
    
    # Database (for pipeline logging)
    database_url: str = Field(
        default="postgresql://opa_user:opa_password@localhost:5432/opa_quotes",
        description="PostgreSQL connection string for pipeline logging"
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings instance (singleton pattern).
    
    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
