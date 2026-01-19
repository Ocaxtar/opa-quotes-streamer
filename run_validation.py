#!/usr/bin/env python3
"""
OPA Quotes Streamer - Script de Validación 1 Hora
Issue: OPA-265
Ejecuta streaming con 100 tickers y genera reporte de métricas
"""
import os
import sys
import time
import asyncio
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path

# Add src to Python path BUT DO NOT import StreamingService yet
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationRunner:
    """Ejecuta validación de streaming y genera reportes."""
    
    def __init__(self, config_path: str):
        """
        Args:
            config_path: Ruta al archivo streaming.yaml
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.start_time = None
        self.service = None
        
    def _load_config(self) -> dict:
        """Carga configuración desde YAML."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuración cargada desde {self.config_path}")
        return config
    
    def _set_environment(self):
        """Configura variables de entorno desde YAML."""
        source_config = self.config['sources']['yahoo_finance']
        
        # Set tickers
        tickers = ','.join(source_config['tickers'])
        os.environ['TICKERS'] = tickers
        
        # Set intervals and limits
        os.environ['POLLING_INTERVAL'] = str(source_config['fetch_interval'])
        os.environ['MAX_REQUESTS_PER_HOUR'] = '2000'  # Safe limit for 100 tickers
        
        # Storage configuration
        if 'publishers' in self.config:
            pub_config = self.config['publishers']['storage']
            os.environ['STORAGE_API_URL'] = pub_config['endpoint']
            os.environ['STORAGE_TIMEOUT'] = str(pub_config['timeout'])
            os.environ['PUBLISHER_ENABLED'] = str(pub_config.get('enabled', True)).lower()
        else:
            os.environ['PUBLISHER_ENABLED'] = 'false'
        
        # Metrics
        if 'metrics' in self.config:
            metrics_config = self.config['metrics']
            os.environ['METRICS_PORT'] = str(metrics_config['port'])
        
        # Logging
        if 'logging' in self.config:
            log_config = self.config['logging']
            os.environ['LOG_LEVEL'] = log_config['level']
        
        logger.info(f"Configurados {len(source_config['tickers'])} tickers")
        logger.info(f"Intervalo de polling: {source_config['fetch_interval']}s")
        logger.info(f"Publisher enabled: {os.environ.get('PUBLISHER_ENABLED', 'true')}")
    
    async def run_validation(self, duration_seconds: int):
        """
        Ejecuta validación por tiempo especificado.
        
        Args:
            duration_seconds: Duración en segundos (3600 para 1 hora)
        """
        logger.info(f"=== Iniciando Validación OPA-265 ===")
        logger.info(f"Duración: {duration_seconds}s ({duration_seconds/60:.0f} minutos)")
        logger.info(f"Tickers: {len(self.config['sources']['yahoo_finance']['tickers'])}")
        
        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(seconds=duration_seconds)
        
        # Set environment BEFORE importing StreamingService
        self._set_environment()
        
        # NOW import after env vars are set
        from opa_quotes_streamer.main import StreamingService
        
        # Create service (will load fresh settings with env vars)
        self.service = StreamingService()
        
        # Create task with timeout
        streaming_task = asyncio.create_task(self.service.start())
        
        try:
            # Wait for duration or until service stops
            await asyncio.wait_for(streaming_task, timeout=duration_seconds)
        except asyncio.TimeoutError:
            logger.info("Tiempo de validación completado")
            await self.service.stop()
        except Exception as e:
            logger.error(f"Error durante validación: {e}", exc_info=True)
            await self.service.stop()
            raise
        
        # Generate report
        self._generate_report()
    
    def _generate_report(self):
        """Genera reporte final de validación."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        report = {
            "validation_id": "OPA-265",
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "duration_minutes": duration.total_seconds() / 60,
            "configuration": {
                "tickers_count": len(self.config['sources']['yahoo_finance']['tickers']),
                "fetch_interval": self.config['sources']['yahoo_finance']['fetch_interval'],
                "batch_size": self.config['sources']['yahoo_finance']['batch_size']
            },
            "metrics": {
                "total_quotes_fetched": self.service.total_quotes_fetched,
                "total_quotes_published": self.service.total_quotes_published,
                "total_cycles": self.service.cycle_count,
                "quotes_per_minute": self.service.total_quotes_published / (duration.total_seconds() / 60)
            },
            "acceptance_criteria": {
                "duration_target": 3600,
                "duration_achieved": duration.total_seconds(),
                "duration_ok": duration.total_seconds() >= 3600 * 0.95,  # 95% tolerance
                "quotes_target": 1000,
                "quotes_achieved": self.service.total_quotes_published,
                "quotes_ok": self.service.total_quotes_published >= 1000
            }
        }
        
        # Save report
        report_path = Path("logs") / f"validation_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"=== REPORTE DE VALIDACIÓN OPA-265 ===")
        logger.info(f"{'='*60}")
        logger.info(f"Duración: {duration.total_seconds():.0f}s ({duration.total_seconds()/60:.1f} min)")
        logger.info(f"Ciclos completados: {self.service.cycle_count}")
        logger.info(f"Quotes fetched: {self.service.total_quotes_fetched}")
        logger.info(f"Quotes publicadas: {self.service.total_quotes_published}")
        logger.info(f"Quotes/min: {report['metrics']['quotes_per_minute']:.1f}")
        logger.info(f"\nCriterios de Aceptación:")
        logger.info(f"  ✓ Duración ≥1h: {'SÍ' if report['acceptance_criteria']['duration_ok'] else 'NO'}")
        logger.info(f"  ✓ Quotes >1000: {'SÍ' if report['acceptance_criteria']['quotes_ok'] else 'NO'}")
        logger.info(f"\nReporte guardado: {report_path}")
        logger.info(f"{'='*60}")


async def main():
    """Entry point."""
    config_path = Path(__file__).parent / "config" / "streaming.yaml"
    
    if not config_path.exists():
        logger.error(f"Archivo de configuración no encontrado: {config_path}")
        sys.exit(1)
    
    # Get duration from config or default to 1 hour
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    duration = config.get('validation', {}).get('duration', 3600)
    
    runner = ValidationRunner(str(config_path))
    
    try:
        await runner.run_validation(duration_seconds=duration)
    except KeyboardInterrupt:
        logger.info("Validación interrumpida por usuario")
        if runner.service:
            await runner.service.stop()
    except Exception as e:
        logger.error(f"Error en validación: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
