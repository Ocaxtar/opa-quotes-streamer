#!/usr/bin/env python3
"""
OPA Quotes Streamer - Benchmark 300 Tickers
Issue: OPA-286
Ejecuta benchmark de streaming para evaluar escalabilidad Python

Métricas capturadas:
- Latencia p50/p95/p99
- Throughput (quotes/segundo)
- Memory usage (MB)
- CPU usage (%)
- Error count
- Gaps detectados
"""
import os
import sys
import time
import asyncio
import json
import yaml
import argparse
import statistics
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from collections import deque

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Ejecuta benchmark de streaming y captura métricas detalladas.
    
    Métricas requeridas (OPA-286):
    - quotes_per_second
    - latency_p50_ms, latency_p95_ms, latency_p99_ms
    - memory_mb
    - cpu_percent
    - errors_count
    - gaps_detected
    """
    
    def __init__(self, config_path: str, tickers: List[str] = None):
        """
        Args:
            config_path: Ruta al archivo streaming.yaml base
            tickers: Lista de tickers (override sobre config)
        """
        self.config_path = config_path
        self.base_config = self._load_config()
        self.override_tickers = tickers
        
        # Métricas de latencia (rolling window)
        self.fetch_latencies_ms: deque = deque(maxlen=10000)
        
        # Contadores
        self.total_quotes = 0
        self.total_errors = 0
        self.gaps_detected = 0
        self.cycles_completed = 0
        
        # Resource tracking
        self.memory_samples: List[float] = []
        self.cpu_samples: List[float] = []
        
        # Timing
        self.start_time = None
        self.service = None
        
        # Gap detection
        self.last_quote_per_ticker: Dict[str, datetime] = {}
        self.expected_interval_seconds = 60  # Based on config
        
    def _load_config(self) -> dict:
        """Carga configuración base desde YAML."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _get_tickers(self) -> List[str]:
        """Obtiene lista de tickers (override o config)."""
        if self.override_tickers:
            return self.override_tickers
        return self.base_config['sources']['yahoo_finance']['tickers']
    
    def _set_environment(self, tickers: List[str]):
        """Configura variables de entorno para el servicio."""
        # Tickers
        os.environ['TICKERS'] = ','.join(tickers)
        
        # Intervals
        source_config = self.base_config['sources']['yahoo_finance']
        os.environ['POLLING_INTERVAL'] = str(source_config.get('fetch_interval', 60))
        
        # Higher request limit for 300 tickers
        # 300 tickers / batch_size * cycles/hour = requests/hour
        # Con 60s interval, ~60 cycles/hora, 300 tickers / 10 batch = 30 requests/cycle
        # 30 * 60 = 1800 requests/hora - ponemos margen
        os.environ['MAX_REQUESTS_PER_HOUR'] = '3000'
        
        # Disable publisher (benchmark solo mide fetch)
        os.environ['PUBLISHER_ENABLED'] = 'false'
        
        # Metrics port
        if 'metrics' in self.base_config:
            os.environ['METRICS_PORT'] = str(self.base_config['metrics'].get('port', 9090))
        
        logger.info(f"Environment configurado para {len(tickers)} tickers")
    
    def _sample_resources(self):
        """Captura sample de CPU y memoria."""
        process = psutil.Process()
        
        # Memory in MB
        memory_mb = process.memory_info().rss / (1024 * 1024)
        self.memory_samples.append(memory_mb)
        
        # CPU percent (interval-based)
        cpu_percent = process.cpu_percent(interval=None)
        self.cpu_samples.append(cpu_percent)
    
    def _detect_gap(self, ticker: str, quote_time: datetime):
        """
        Detecta gap si el intervalo entre quotes es mayor al esperado.
        
        Un gap indica posible pérdida de datos o timeout.
        """
        if ticker in self.last_quote_per_ticker:
            last_time = self.last_quote_per_ticker[ticker]
            interval = (quote_time - last_time).total_seconds()
            
            # Gap si > 2x intervalo esperado
            if interval > self.expected_interval_seconds * 2:
                self.gaps_detected += 1
                logger.warning(f"Gap detectado para {ticker}: {interval:.0f}s desde última quote")
        
        self.last_quote_per_ticker[ticker] = quote_time
    
    async def run_benchmark(self, duration_seconds: int) -> Dict[str, Any]:
        """
        Ejecuta benchmark por duración especificada.
        
        Args:
            duration_seconds: Duración en segundos
            
        Returns:
            Diccionario con métricas del benchmark
        """
        tickers = self._get_tickers()
        logger.info(f"=== Iniciando Benchmark OPA-286 ===")
        logger.info(f"Tickers: {len(tickers)}")
        logger.info(f"Duración objetivo: {duration_seconds}s ({duration_seconds/3600:.1f} horas)")
        
        self.start_time = datetime.now()
        self._set_environment(tickers)
        
        # Import after env setup
        from opa_quotes_streamer.main import StreamingService
        
        self.service = StreamingService()
        
        # Override fetch tracking
        original_fetch = self.service.source.fetch_quotes
        
        async def instrumented_fetch(ticker_list):
            """Wrapper para medir latencia de cada fetch."""
            fetch_start = time.time()
            try:
                quotes = await original_fetch(ticker_list)
                latency_ms = (time.time() - fetch_start) * 1000
                self.fetch_latencies_ms.append(latency_ms)
                
                if quotes:
                    self.total_quotes += len(quotes)
                    # Gap detection per ticker
                    for q in quotes:
                        if hasattr(q, 'symbol') and hasattr(q, 'timestamp'):
                            self._detect_gap(q.symbol, q.timestamp)
                
                return quotes
            except Exception as e:
                self.total_errors += 1
                logger.error(f"Error en fetch: {e}")
                raise
        
        self.service.source.fetch_quotes = instrumented_fetch
        
        # Resource sampling task
        async def resource_sampler():
            """Sample resources cada 5 segundos."""
            while True:
                self._sample_resources()
                await asyncio.sleep(5)
        
        # Start resource sampler
        sampler_task = asyncio.create_task(resource_sampler())
        
        # Start streaming
        streaming_task = asyncio.create_task(self.service.start())
        
        try:
            await asyncio.wait_for(streaming_task, timeout=duration_seconds)
        except asyncio.TimeoutError:
            logger.info("Tiempo de benchmark completado")
        except asyncio.CancelledError:
            logger.info("Benchmark cancelado")
        finally:
            sampler_task.cancel()
            try:
                await sampler_task
            except asyncio.CancelledError:
                pass
            await self.service.stop()
        
        # Generate metrics
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calcula métricas finales del benchmark."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Latency percentiles
        latencies = list(self.fetch_latencies_ms)
        if latencies:
            latencies_sorted = sorted(latencies)
            p50 = latencies_sorted[int(len(latencies_sorted) * 0.50)]
            p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
            p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        else:
            p50 = p95 = p99 = 0.0
        
        # Resource stats
        memory_avg = statistics.mean(self.memory_samples) if self.memory_samples else 0.0
        memory_max = max(self.memory_samples) if self.memory_samples else 0.0
        cpu_avg = statistics.mean(self.cpu_samples) if self.cpu_samples else 0.0
        cpu_max = max(self.cpu_samples) if self.cpu_samples else 0.0
        
        metrics = {
            "benchmark_id": "OPA-286",
            "timestamp": end_time.isoformat(),
            "configuration": {
                "tickers_count": len(self._get_tickers()),
                "duration_seconds": duration,
                "duration_hours": duration / 3600,
                "polling_interval": self.base_config['sources']['yahoo_finance'].get('fetch_interval', 60)
            },
            "throughput": {
                "total_quotes": self.total_quotes,
                "quotes_per_second": self.total_quotes / duration if duration > 0 else 0,
                "quotes_per_minute": (self.total_quotes / duration) * 60 if duration > 0 else 0,
                "cycles_completed": self.service.cycle_count if self.service else 0
            },
            "latency_ms": {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "samples": len(latencies)
            },
            "resources": {
                "memory_avg_mb": round(memory_avg, 2),
                "memory_max_mb": round(memory_max, 2),
                "cpu_avg_percent": round(cpu_avg, 2),
                "cpu_max_percent": round(cpu_max, 2)
            },
            "reliability": {
                "errors_count": self.total_errors,
                "gaps_detected": self.gaps_detected,
                "error_rate_percent": (self.total_errors / max(1, self.total_quotes + self.total_errors)) * 100
            }
        }
        
        return metrics
    
    def generate_report_markdown(self, metrics: Dict[str, Any], output_path: str) -> str:
        """
        Genera reporte en formato Markdown.
        
        Args:
            metrics: Métricas del benchmark
            output_path: Ruta para guardar el reporte
            
        Returns:
            Contenido del reporte
        """
        tickers_count = metrics['configuration']['tickers_count']
        duration_hours = metrics['configuration']['duration_hours']
        
        # Determinar si escala
        # Criterios: p99 < 200ms, errors < 1%, gaps < 5
        p99_ok = metrics['latency_ms']['p99'] < 200
        errors_ok = metrics['reliability']['error_rate_percent'] < 1
        gaps_ok = metrics['reliability']['gaps_detected'] < 5
        python_scales = p99_ok and errors_ok and gaps_ok
        
        # Determinar recomendación
        if python_scales:
            recommendation = "✅ **Continuar con Python** - Escala satisfactoriamente"
            recommendation_detail = "Python maneja 300 tickers sin degradación significativa."
        elif metrics['latency_ms']['p99'] > 500:
            recommendation = "⚠️ **Migrar a Rust** - Latencia crítica"
            recommendation_detail = f"Latencia p99 ({metrics['latency_ms']['p99']:.0f}ms) excede umbrales aceptables."
        else:
            recommendation = "🔶 **Evaluar optimizaciones Python primero**"
            recommendation_detail = "Hay margen de mejora antes de migrar a Rust."
        
        report = f"""# Benchmark Streaming Python - 300 Tickers

**Issue**: OPA-286
**Fecha**: {metrics['timestamp']}
**Repositorio**: opa-quotes-streamer

---

## 📊 Resumen Ejecutivo

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| Tickers | {tickers_count} | 300 | {'✅' if tickers_count >= 300 else '⚠️'} |
| Duración | {duration_hours:.2f}h | 2h | {'✅' if duration_hours >= 1.9 else '⚠️'} |
| Latencia p99 | {metrics['latency_ms']['p99']:.0f}ms | <200ms | {'✅' if p99_ok else '❌'} |
| Error rate | {metrics['reliability']['error_rate_percent']:.2f}% | <1% | {'✅' if errors_ok else '❌'} |
| Gaps | {metrics['reliability']['gaps_detected']} | <5 | {'✅' if gaps_ok else '❌'} |

### Pregunta Principal

> **¿Python escala a 300 tickers?** {'**SÍ**' if python_scales else '**NO**'}

---

## 🔢 Métricas Detalladas

### Throughput

- **Total quotes**: {metrics['throughput']['total_quotes']:,}
- **Quotes/segundo**: {metrics['throughput']['quotes_per_second']:.2f}
- **Quotes/minuto**: {metrics['throughput']['quotes_per_minute']:.1f}
- **Ciclos completados**: {metrics['throughput']['cycles_completed']}

### Latencia (ms)

| Percentil | Valor |
|-----------|-------|
| p50 | {metrics['latency_ms']['p50']:.2f}ms |
| p95 | {metrics['latency_ms']['p95']:.2f}ms |
| p99 | {metrics['latency_ms']['p99']:.2f}ms |

### Recursos

| Recurso | Promedio | Máximo |
|---------|----------|--------|
| Memoria | {metrics['resources']['memory_avg_mb']:.1f} MB | {metrics['resources']['memory_max_mb']:.1f} MB |
| CPU | {metrics['resources']['cpu_avg_percent']:.1f}% | {metrics['resources']['cpu_max_percent']:.1f}% |

### Fiabilidad

- **Errores totales**: {metrics['reliability']['errors_count']}
- **Gaps detectados**: {metrics['reliability']['gaps_detected']}
- **Tasa de error**: {metrics['reliability']['error_rate_percent']:.2f}%

---

## 🎯 Recomendación

{recommendation}

{recommendation_detail}

### Próximos pasos

1. {'Proceder con OPA-288 (ampliar a 300 tickers en producción)' if python_scales else 'Documentar en ADR-019 justificación para Rust'}
2. {'Monitorear métricas en producción' if python_scales else 'Evaluar timeline migración Rust'}
3. Actualizar OPA-289 con esta decisión

---

## 📎 Datos Crudos

```json
{json.dumps(metrics, indent=2)}
```

---

*Generado automáticamente por `scripts/benchmark_streaming.py`*
"""
        
        # Save report
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Reporte guardado en: {output_path}")
        return report


def get_sp500_top300_tickers() -> List[str]:
    """
    Retorna lista de 300 tickers más líquidos del S&P 500.
    
    Basado en:
    - Capitalización de mercado
    - Volumen promedio diario
    - Liquidez
    
    Nota: Esta lista está hardcodeada basándose en OPA-285.
    En futuras versiones, se cargará desde archivo externo.
    """
    return [
        # Technology (50)
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
        "CSCO", "ADBE", "CRM", "INTC", "AMD", "QCOM", "TXN", "IBM", "INTU", "NOW",
        "AMAT", "LRCX", "KLAC", "SNPS", "CDNS", "MU", "ADI", "MCHP", "FTNT", "PANW",
        "NXPI", "MPWR", "KEYS", "ANSS", "SWKS", "CTSH", "IT", "HPQ", "HPE", "DELL",
        "NTAP", "JNPR", "WDC", "STX", "FFIV", "AKAM", "ZBRA", "GEN", "EPAM", "ENPH",
        
        # Financials (45)
        "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "SPGI",
        "BX", "USB", "PNC", "TFC", "COF", "CME", "ICE", "MCO", "AIG", "MET",
        "PRU", "AFL", "TRV", "CB", "ALL", "PGR", "HIG", "AJG", "MMC", "AON",
        "MSCI", "FIS", "FISV", "GPN", "PYPL", "V", "MA", "AMP", "RJF", "NTRS",
        "STT", "BK", "CFG", "RF", "FITB",
        
        # Healthcare (45)
        "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "PFE", "DHR", "BMY",
        "AMGN", "GILD", "CVS", "CI", "ISRG", "VRTX", "REGN", "BIIB", "MRNA", "MDT",
        "SYK", "BSX", "ZBH", "EW", "BDX", "DXCM", "IDXX", "IQV", "A", "MTD",
        "WAT", "HOLX", "ALGN", "TECH", "RVTY", "CRL", "DGX", "LH", "HCA", "ELV",
        "CNC", "MOH", "HUM", "MCK", "CAH",
        
        # Consumer Discretionary (35)
        "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "GM", "F", "TGT",
        "ROST", "CMG", "DHI", "LEN", "PHM", "NVR", "ORLY", "AZO", "BBY", "DRI",
        "MAR", "HLT", "WYNN", "LVS", "MGM", "RCL", "CCL", "EXPE", "ABNB", "UBER",
        "LYFT", "DPZ", "YUM", "QSR", "DARDEN",
        
        # Consumer Staples (25)
        "WMT", "PG", "KO", "PEP", "COST", "PM", "MO", "CL", "EL", "KMB",
        "MDLZ", "GIS", "K", "HSY", "CPB", "SJM", "CAG", "HRL", "TSN", "KHC",
        "TAP", "STZ", "BF.B", "ADM", "BG",
        
        # Energy (25)
        "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO", "OXY", "PXD",
        "DVN", "FANG", "HES", "HAL", "BKR", "KMI", "WMB", "OKE", "ET", "TRGP",
        "LNG", "MRO", "APA", "CTRA", "EQT",
        
        # Industrials (40)
        "BA", "CAT", "UNP", "HON", "UPS", "RTX", "LMT", "DE", "GE", "MMM",
        "EMR", "ITW", "ETN", "PH", "ROK", "CMI", "PCAR", "FAST", "GWW", "SWK",
        "IR", "DOV", "XYL", "NDSN", "IEX", "AME", "ROP", "TT", "CARR", "OTIS",
        "TDG", "HWM", "TXT", "NOC", "GD", "LHX", "LDOS", "J", "FDX", "CSX",
        
        # Communication Services (15)
        "DIS", "CMCSA", "NFLX", "T", "VZ", "TMUS", "CHTR", "EA", "TTWO", "WBD",
        "FOXA", "FOX", "OMC", "IPG", "PARA",
        
        # Utilities (10)
        "NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "ED", "PEG",
        
        # Real Estate (10)
        "PLD", "AMT", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB",
    ]


async def main():
    """Entry point para benchmark."""
    parser = argparse.ArgumentParser(
        description="Benchmark streaming 300 tickers (OPA-286)"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help="Lista de tickers separados por coma (default: S&P 500 top 300)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=7200,  # 2 horas por defecto
        help="Duración del benchmark en segundos (default: 7200 = 2 horas)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/benchmark-300-tickers.json",
        help="Ruta para guardar métricas JSON"
    )
    parser.add_argument(
        "--report",
        type=str,
        default="reports/benchmark-300-tickers-report.md",
        help="Ruta para guardar reporte Markdown"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Modo rápido: 5 minutos (para testing)"
    )
    
    args = parser.parse_args()
    
    # Prepare tickers
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",")]
    else:
        tickers = get_sp500_top300_tickers()
    
    # Duration
    duration = 300 if args.quick else args.duration  # 5 min en modo quick
    
    # Config path
    config_path = Path(__file__).parent.parent / "config" / "streaming.yaml"
    
    if not config_path.exists():
        logger.error(f"Config no encontrado: {config_path}")
        sys.exit(1)
    
    logger.info(f"Config: {config_path}")
    logger.info(f"Tickers: {len(tickers)}")
    logger.info(f"Duración: {duration}s ({duration/60:.1f} min)")
    
    # Run benchmark
    runner = BenchmarkRunner(str(config_path), tickers)
    
    try:
        metrics = await runner.run_benchmark(duration_seconds=duration)
        
        # Save JSON metrics
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Métricas guardadas: {output_path}")
        
        # Generate markdown report
        report = runner.generate_report_markdown(metrics, args.report)
        
        # Print summary
        print("\n" + "="*60)
        print("BENCHMARK COMPLETADO - OPA-286")
        print("="*60)
        print(f"Tickers: {metrics['configuration']['tickers_count']}")
        print(f"Duración: {metrics['configuration']['duration_hours']:.2f}h")
        print(f"Quotes totales: {metrics['throughput']['total_quotes']:,}")
        print(f"Latencia p99: {metrics['latency_ms']['p99']:.2f}ms")
        print(f"Memoria máx: {metrics['resources']['memory_max_mb']:.1f}MB")
        print(f"Errores: {metrics['reliability']['errors_count']}")
        print(f"Gaps: {metrics['reliability']['gaps_detected']}")
        print("="*60)
        print(f"\nReporte: {args.report}")
        print(f"Métricas: {args.output}")
        
    except KeyboardInterrupt:
        logger.info("Benchmark interrumpido por usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error en benchmark: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
