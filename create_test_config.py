#!/usr/bin/env python3
"""
Quick smoke test - 1 minute validation
Issue: OPA-265
"""
import sys
import yaml
from pathlib import Path

# Modify config for quick test
config_path = Path(__file__).parent / "config" / "streaming.yaml"

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Reduce to 10 tickers for quick test
config['sources']['yahoo_finance']['tickers'] = config['sources']['yahoo_finance']['tickers'][:10]
config['validation']['duration'] = 60  # 1 minute

# Save temp config
temp_config_path = Path(__file__).parent / "config" / "streaming_test.yaml"
with open(temp_config_path, 'w') as f:
    yaml.dump(config, f)

print(f"✓ Test config created: {temp_config_path}")
print(f"  Tickers: {len(config['sources']['yahoo_finance']['tickers'])}")
print(f"  Duration: {config['validation']['duration']}s")
print("\nRun: poetry run python run_validation_test.py")
