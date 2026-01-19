#!/usr/bin/env python3
"""
Test runner - Uses streaming_test.yaml for quick validation
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncio
from run_validation import ValidationRunner

async def main():
    config_path = Path(__file__).parent / "config" / "streaming_test.yaml"
    
    if not config_path.exists():
        print("ERROR: Test config not found. Run: python create_test_config.py")
        sys.exit(1)
    
    runner = ValidationRunner(str(config_path))
    await runner.run_validation(duration_seconds=60)

if __name__ == "__main__":
    asyncio.run(main())
