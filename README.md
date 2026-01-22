# opa-quotes-streamer

[![CI Status](https://github.com/Ocaxtar/opa-quotes-streamer/workflows/CI/badge.svg)](https://github.com/Ocaxtar/opa-quotes-streamer/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Real-time quote streaming service for OPA_Machine ecosystem (Módulo 5 - Cotización).

**Cobertura actual**: 300 tickers S&P 500 más líquidos  
**Fase 1**: Python implementation with yfinance (polling 60s) ✅  
**Fase 2**: Decisión: Continuar con Python (ADR-019)

## 📋 Descripción

`opa-quotes-streamer` es el servicio de **ingesta en tiempo real** de cotizaciones del Módulo 5 (Cotización). Conecta con fuentes de datos financieros (yfinance en Fase 1) y transmite cotizaciones actualizadas a `opa-quotes-storage` mediante arquitectura async.

### Responsabilidades

1. **Streaming continuo**: Conectar a fuentes de datos y mantener stream activo
2. **Rate limiting**: Respetar límites de APIs (yfinance: ~2000 req/h)
3. **Normalización**: Transformar datos a formato estándar (schema de contratos)
4. **Resiliencia**: Reconexión automática, backoff exponencial, circuit breaker
5. **Monitorización**: Métricas Prometheus (tickers activos, latencia, errores)

### Flujo de Datos

```
yfinance API → opa-quotes-streamer → opa-quotes-storage (TimescaleDB)
                     ↓
               Redis Pub/Sub (CloudEvents 1.0)
                     ↓
            opa-capacity-api, otros servicios
                     ↓
            Métricas (Prometheus)
```

## 🏗️ Arquitectura

### Stack Tecnológico (Fase 1)

| Componente | Tecnología | Versión | Propósito |
|------------|------------|---------|-----------|
| **Lenguaje** | Python | 3.12 | Async/await streaming |
| **Data source** | yfinance | 0.2.32+ | Yahoo Finance API |
| **HTTP client** | aiohttp | 3.9+ | Async HTTP requests |
| **WebSockets** | websockets | 12.0+ | Real-time streaming |
| **Data manipulation** | pandas | 2.1+ | Quote transformation |
| **Validation** | Pydantic | 2.5+ | Schema validation |
| **Storage client** | httpx | 0.25+ | opa-quotes-storage API |
| **Logging** | PipelineLogger | custom | Structured logging |

### Componentes

```
src/opa_quotes_streamer/
├── main.py                  # StreamingService (entry point)
├── config.py                # Settings (tickers, intervals, rate limits)
├── logging_setup.py         # Logging configuration
├── sources/
│   ├── base.py              # BaseDataSource (interface)
│   └── yfinance_source.py   # YFinanceSource (Fase 1)
├── publishers/
│   ├── base.py              # BasePublisher (interface)
│   ├── storage_publisher.py # TimescalePublisher (HTTP → storage)
│   └── redis_publisher.py   # RedisPublisher (CloudEvents → Redis Pub/Sub)
├── models/
│   ├── quote.py             # Quote (Pydantic model)
│   └── stream_event.py      # StreamEvent (lifecycle events)
└── utils/
    ├── rate_limiter.py      # RateLimiter (token bucket)
    └── circuit_breaker.py   # CircuitBreaker (resiliency)
```

### Estrategia de Streaming

**Fase 1 (Python)**: Polling yfinance cada 5s (limitación de API gratuita)

```python
# Polling loop
while running:
    quotes = await yfinance_source.fetch_quotes(tickers)
    await storage_publisher.publish_batch(quotes)
    await asyncio.sleep(5)  # Rate limiting
```

**Fase 2 (Rust)**: WebSocket real-time (migración futura)

- Tokio async runtime
- WebSocket protocol (IEX Cloud, Alpha Vantage)
- Sub-second latency (<100ms)
- 1000+ concurrent tickers

## 🚀 Setup Local

### Prerrequisitos

- **Python 3.12**
- **Poetry 1.7+**
- **Docker Compose**
- **opa-quotes-storage** en ejecución (o mock)

### Instalación

```powershell
# Clonar repositorio
git clone https://github.com/Ocaxtar/opa-quotes-streamer.git
Set-Location opa-quotes-streamer

# Instalar dependencias
poetry install

# Configurar entorno
Copy-Item .env.example .env
# Editar .env con configuración local
```

### Configuración (.env)

```env
# Tickers a monitorizar (ver config/streaming.yaml para lista completa de 300)
TICKERS=AAPL,MSFT,GOOGL,AMZN,TSLA,META,NVDA,JPM,V,WMT,...

# Intervalo de polling (segundos) - optimizado para 300 tickers
POLLING_INTERVAL=60

# opa-quotes-storage endpoint
STORAGE_API_URL=http://localhost:8000

# Redis Pub/Sub configuration (Fase 2)
REDIS_URL=redis://localhost:6381
REDIS_CHANNEL=quotes-stream
REDIS_PUBLISHER_ENABLED=true

# Rate limiting (aumentado para 300 tickers)
MAX_REQUESTS_PER_HOUR=3000

# Logging
LOG_LEVEL=INFO
```

### Ejecución

#### Desarrollo (Python)

```powershell
# Activar entorno
poetry shell

# Ejecutar streamer
python -m opa_quotes_streamer.main

# Logs esperados:
# INFO - Starting opa-quotes-streamer v0.1.0
# INFO - Streaming 300 tickers: AAPL, MSFT, GOOGL...
# INFO - Fetched 289 quotes in 30.2s
# INFO - Cycle 1 completed
```

#### Docker Compose

#### Docker Compose

```powershell
# Build e iniciar servicios (streamer + storage mock + prometheus)
docker-compose up -d

# Ver logs del streamer
docker-compose logs -f streamer

# Verificar métricas
curl http://localhost:8001/metrics | grep streamer

# Verificar salud del streamer
docker-compose ps streamer

# Iniciar con Prometheus para monitoreo
docker-compose --profile monitoring up -d

# Ver dashboard de Prometheus
# Navegar a http://localhost:9090

# Parar servicios
docker-compose down
```

**Servicios disponibles:**
- `streamer`: opa-quotes-streamer (puerto 8001)
- `storage-mock`: MockServer simulando opa-quotes-storage (puerto 8000)
- `prometheus`: Prometheus metrics scraper (puerto 9090) - profile `monitoring`

## 🧪 Testing

### Estrategia de Tests

| Tipo | Alcance | Mocks | Propósito |
|------|---------|-------|-----------|
| **Unit** | Fuentes, publishers, utils | Todo | Lógica individual |
| **Integration** | End-to-end | yfinance, storage API | Flujo completo |
| **Load** | Volumen | Storage API | Resiliencia streaming |

### Ejecución

```powershell
# Tests unitarios
poetry run pytest tests/unit -v

# Tests de integración (requiere docker-compose up)
poetry run pytest tests/integration -v

# Coverage
poetry run pytest --cov=opa_quotes_streamer --cov-report=html

# Tests específicos
poetry run pytest tests/unit/test_yfinance_source.py -v
```

### Ejemplo de Test

```python
# tests/unit/test_yfinance_source.py
import pytest
from opa_quotes_streamer.sources.yfinance_source import YFinanceSource

@pytest.mark.asyncio
async def test_fetch_quotes_success():
    source = YFinanceSource(tickers=["AAPL", "MSFT"])
    
    quotes = await source.fetch_quotes()
    
    assert len(quotes) == 2
    assert quotes[0].ticker == "AAPL"
    assert quotes[0].price > 0
    assert quotes[0].timestamp is not None
```

## 📊 Monitorización

### Métricas Prometheus

Expuestas en `http://localhost:8001/metrics`

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `streamer_quotes_fetched_total` | Counter | Total quotes fetched desde yfinance |
| `streamer_quotes_published_total` | Counter | Total quotes enviadas a storage |
| `streamer_fetch_duration_seconds` | Histogram | Latencia fetch de yfinance |
| `streamer_publish_duration_seconds` | Histogram | Latencia publish a storage |
| `streamer_errors_total` | Counter | Errores por tipo (fetch, publish, validation) |
| `streamer_active_tickers` | Gauge | Tickers actualmente monitorizados |
| `streamer_rate_limit_hits_total` | Counter | Veces que hit rate limit |

### Health Check

```powershell
# Endpoint /health
Invoke-RestMethod http://localhost:8001/health

# Respuesta esperada
{
  "status": "ok",
  "version": "0.1.0",
  "repository": "opa-quotes-streamer",
  "active_tickers": 10,
  "last_fetch": "2025-12-22T11:00:00Z",
  "uptime_seconds": 3600
}
```

## 🔗 Integración con Otros Servicios

### Upstream (Fuentes de Datos)

| Servicio | Protocolo | Propósito | Fase |
|----------|-----------|-----------|------|
| **yfinance** | HTTP (polling) | Cotizaciones US equities | Fase 1 |
| **IEX Cloud** | WebSocket (planned) | Real-time streaming | Fase 2 (Rust) |
| **Alpha Vantage** | WebSocket (planned) | Crypto + Forex | Fase 2 (Rust) |

### Downstream (Consumidores)

| Servicio | Protocolo | Datos Enviados | Contrato |
|----------|-----------|----------------|----------|
| **opa-quotes-storage** | HTTP POST | Batches de quotes (10-100) | `/quotes/batch` |

### Contratos de API

Este servicio actúa como **Producer** en el flujo de cotizaciones:

#### POST /quotes/batch (Producer)

**Contract**: [Quotes Batch Contract](https://github.com/Ocaxtar/opa-supervisor/blob/main/docs/contracts/apis/quotes-batch.md)

- **Role**: Producer (genera y envía quotes)
- **Consumer**: opa-quotes-api
- **Invariants**: INV-001 to INV-007 (Producer guarantees)
- **Validation**: Unit tests in `tests/test_storage_publisher.py`

**Contract invariants satisfied**:
- ✅ **INV-001**: Send quotes array (non-empty, 1-1000 items)
- ✅ **INV-002**: Validate ticker format `^[A-Z]{1,5}$` before sending
- ✅ **INV-003**: Timestamp in ISO 8601 UTC format
- ✅ **INV-004**: Include close price (positive float)
- ✅ **INV-005**: Include source field (`yfinance`, `fmp`, or `manual`)
- ✅ **INV-006**: Respect 1000 quotes/batch limit (batch splitting)
- ✅ **INV-007**: Send `Content-Type: application/json` header

**Testing contract compliance**:
```powershell
# Verify producer invariants
pytest tests/test_storage_publisher.py::test_batch_invariants -v

# Test payload validation
pytest tests/test_storage_publisher.py::test_ticker_format_validation -v

# Integration test (requires opa-quotes-api running)
pytest tests/integration/test_end_to_end_flow.py -v
```

**Example valid payload sent**:
```json
{
  "quotes": [
    {
      "ticker": "AAPL",
      "timestamp": "2026-01-13T04:00:00Z",
      "close": 175.23,
      "open": 174.50,
      "high": 176.00,
      "low": 174.20,
      "volume": 52341000,
      "source": "yfinance"
    }
  ]
}
```

**Pre-send validation logic**:
```python
# src/opa_quotes_streamer/publishers/storage_publisher.py
def validate_quote_batch(quotes: List[Quote]) -> None:
    """Validate batch before sending (INV-001 to INV-007)"""
    
    # INV-001: Non-empty array
    if not quotes or len(quotes) == 0:
        raise ValueError("Quotes array cannot be empty")
    
    # INV-006: Max 1000 quotes/batch
    if len(quotes) > 1000:
        raise ValueError(f"Batch too large: {len(quotes)} > 1000")
    
    for quote in quotes:
        # INV-002: Ticker format
        if not re.match(r'^[A-Z]{1,5}$', quote.ticker):
            raise ValueError(f"Invalid ticker format: {quote.ticker}")
        
        # INV-003: ISO 8601 UTC
        if quote.timestamp.tzinfo != timezone.utc:
            raise ValueError(f"Timestamp must be UTC: {quote.timestamp}")
        
        # INV-004: Positive close
        if quote.close <= 0:
            raise ValueError(f"Close price must be positive: {quote.close}")
        
        # INV-005: Valid source
        if quote.source not in ["yfinance", "fmp", "manual"]:
            raise ValueError(f"Invalid source: {quote.source}")
```

**Batch splitting for large datasets**:
```python
# If yfinance returns >1000 quotes, split into multiple batches
MAX_BATCH_SIZE = 1000

async def publish_large_batch(quotes: List[Quote]):
    for i in range(0, len(quotes), MAX_BATCH_SIZE):
        batch = quotes[i:i + MAX_BATCH_SIZE]
        await storage_publisher.publish_batch(batch)  # Respects INV-006
```

#### Other Contracts

Ver contrato de datos: [`docs/contracts/data-models/quotes.md`](../opa-supervisor/docs/contracts/data-models/quotes.md) en repositorio supervisor.

**Schema Quote**:

```python
{
  "ticker": "AAPL",
  "price": 178.45,
  "volume": 52341000,
  "timestamp": "2025-12-22T15:30:00Z",
  "source": "yfinance"
}
```

## 🛠️ Desarrollo

### Estructura de Branches

- `main`: Código estable (siempre desplegable)
- `feature/OPA-XXX-descripcion`: Nuevas features
- `fix/OPA-XXX-descripcion`: Bug fixes

### Convenciones

1. **Commits**: `OPA-XXX: Descripción en imperativo`
2. **PRs**: Título = descripción issue Linear
3. **Tests**: Obligatorios para toda lógica de negocio
4. **Linting**: `ruff` antes de commit

### Añadir Nuevo Data Source

```python
# 1. Crear clase en sources/
from opa_quotes_streamer.sources.base import BaseDataSource

class NewSource(BaseDataSource):
    async def fetch_quotes(self, tickers: List[str]) -> List[Quote]:
        # Implementación
        pass

# 2. Registrar en config.py
AVAILABLE_SOURCES = {
    "yfinance": YFinanceSource,
    "newsource": NewSource,
}

# 3. Tests unitarios
# tests/unit/test_newsource.py
```

## 🐛 Troubleshooting

### Error: "Rate limit exceeded"

**Síntoma**: `streamer_rate_limit_hits_total` incrementa

**Solución**:
```powershell
# Aumentar POLLING_INTERVAL en .env
POLLING_INTERVAL=10  # De 5s a 10s

# Reducir tickers
TICKERS=AAPL,MSFT,GOOGL  # De 10 a 3
```

### Error: "Connection refused to storage"

**Síntoma**: `streamer_errors_total{type="publish"}` incrementa

**Solución**:
```powershell
# Verificar opa-quotes-storage está corriendo
Invoke-RestMethod http://localhost:8000/health

# Verificar configuración .env
STORAGE_API_URL=http://localhost:8000  # Debe coincidir con docker-compose
```

### Latencia alta (>5s fetch)

**Síntoma**: `streamer_fetch_duration_seconds` p99 > 5s

**Diagnóstico**:
```powershell
# Ver logs de yfinance
docker-compose logs -f streamer | Select-String "yfinance"

# Posibles causas:
# - Red lenta
# - Rate limiting de Yahoo
# - Demasiados tickers (>50)
```

## 📖 Roadmap

### Fase 1: Python Implementation ✅

- [x] Scaffolding completo
- [x] YFinanceSource (fetch quotes con rate limiting)
- [x] StoragePublisher (POST a opa-quotes-storage)
- [x] StreamingService con graceful shutdown
- [x] RateLimiter (token bucket) + CircuitBreaker
- [x] Tests unitarios + integración
- [x] Docker Compose + CI/CD
- [x] **OPA-265**: Validación 100 tickers
- [x] **OPA-286**: Benchmark 300 tickers
- [x] **OPA-288**: Ampliar a 300 tickers S&P 500

**Resultado**: 300 tickers, polling 60s, latencia batch ~30-40s, memoria ~240MB

### Fase 2: Optimización (Decidido: Continuar Python)

- [x] **OPA-289**: ADR-019 Decisión Rust vs Python → **Python suficiente**
- [ ] Optimizar batch processing
- [ ] Redis Pub/Sub para distribución
- [ ] Escalabilidad horizontal (múltiples instancias)

Ver [`ROADMAP.md`](./ROADMAP.md) para detalles completos.

## 🤝 Contribución

Este es un repositorio privado del equipo OPA. Para contribuir:

1. Crear issue en Linear (proyecto `opa-quotes-streamer`)
2. Crear branch desde `main`
3. Implementar + tests
4. PR con referencia a issue (`OPA-XXX`)
5. Review + merge

Ver [`AGENTS.md`](./AGENTS.md) para guías de agentes IA.

## 📄 Licencia

MIT License - Ver [LICENSE](../opa-supervisor/LICENSE) en repositorio supervisor.

## 🔗 Enlaces

- **Repositorio Supervisor**: [OPA_Machine](https://github.com/Ocaxtar/opa-supervisor)
- **Contratos**: [`docs/contracts/`](../opa-supervisor/docs/contracts/)
- **ADRs**: [`docs/adr/`](../opa-supervisor/docs/adr/)
- **Linear**: [Proyecto opa-quotes-streamer](https://linear.app/opa-machine/team/OPA/project/opa-quotes-streamer)
