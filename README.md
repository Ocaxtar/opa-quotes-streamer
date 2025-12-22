# opa-quotes-streamer

[![CI Status](https://github.com/Ocaxtar/opa-quotes-streamer/workflows/CI/badge.svg)](https://github.com/Ocaxtar/opa-quotes-streamer/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Real-time quote streaming service for OPA_Machine ecosystem (Módulo 5 - Cotización).

**Fase 1**: Python implementation with yfinance + WebSockets  
**Fase 2**: Rust migration for ultra-low latency (planned)

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
│   └── storage_publisher.py # TimescalePublisher (HTTP → storage)
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

```bash
# Clonar repositorio
git clone https://github.com/Ocaxtar/opa-quotes-streamer.git
cd opa-quotes-streamer

# Instalar dependencias
poetry install

# Configurar entorno
cp .env.example .env
# Editar .env con configuración local
```

### Configuración (.env)

```bash
# Tickers a monitorizar (separados por coma)
TICKERS=AAPL,MSFT,GOOGL,AMZN,TSLA,META,NVDA,JPM,V,WMT

# Intervalo de polling (segundos)
POLLING_INTERVAL=5

# opa-quotes-storage endpoint
STORAGE_API_URL=http://localhost:8000

# Rate limiting
MAX_REQUESTS_PER_HOUR=2000

# Logging
LOG_LEVEL=INFO
```

### Ejecución

#### Desarrollo (Python)

```bash
# Activar entorno
poetry shell

# Ejecutar streamer
python -m opa_quotes_streamer.main

# Logs esperados:
# INFO - Starting opa-quotes-streamer v0.1.0
# INFO - Streaming 10 tickers: AAPL, MSFT, GOOGL...
# INFO - Fetched 10 quotes in 1.2s
# INFO - Published 10 quotes to storage
```

#### Docker Compose

```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver logs del streamer
docker-compose logs -f streamer

# Verificar salud
curl http://localhost:8001/health
```

## 🧪 Testing

### Estrategia de Tests

| Tipo | Alcance | Mocks | Propósito |
|------|---------|-------|-----------|
| **Unit** | Fuentes, publishers, utils | Todo | Lógica individual |
| **Integration** | End-to-end | yfinance, storage API | Flujo completo |
| **Load** | Volumen | Storage API | Resiliencia streaming |

### Ejecución

```bash
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

```bash
# Endpoint /health
curl http://localhost:8001/health

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

### Contratos

Ver [`docs/contracts/data-models/quotes.md`](../OPA_Machine/docs/contracts/data-models/quotes.md) en repositorio supervisor.

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
```bash
# Aumentar POLLING_INTERVAL en .env
POLLING_INTERVAL=10  # De 5s a 10s

# Reducir tickers
TICKERS=AAPL,MSFT,GOOGL  # De 10 a 3
```

### Error: "Connection refused to storage"

**Síntoma**: `streamer_errors_total{type="publish"}` incrementa

**Solución**:
```bash
# Verificar opa-quotes-storage está corriendo
curl http://localhost:8000/health

# Verificar configuración .env
STORAGE_API_URL=http://localhost:8000  # Debe coincidir con docker-compose
```

### Latencia alta (>5s fetch)

**Síntoma**: `streamer_fetch_duration_seconds` p99 > 5s

**Diagnóstico**:
```bash
# Ver logs de yfinance
docker-compose logs -f streamer | grep "yfinance"

# Posibles causas:
# - Red lenta
# - Rate limiting de Yahoo
# - Demasiados tickers (>50)
```

## 📖 Roadmap

### Fase 1: Python Implementation (Actual)

- [x] Scaffolding completo
- [ ] **OPA-194**: YFinanceSource (fetch quotes con rate limiting)
- [ ] **OPA-195**: StoragePublisher (POST a opa-quotes-storage)
- [ ] **OPA-196**: StreamingService con graceful shutdown
- [ ] **OPA-197**: RateLimiter (token bucket) + CircuitBreaker
- [ ] **OPA-198**: Tests unitarios + integración
- [ ] **OPA-199**: Docker Compose + CI/CD

**Target**: 10-50 tickers, polling 5s, latencia total <2s

### Fase 2: Rust Migration (Futuro)

- [ ] Rust POC con Tokio + WebSocket
- [ ] IEX Cloud integration (real-time)
- [ ] Migración gradual (Python → Rust)
- [ ] 1000+ tickers concurrentes
- [ ] Sub-second latency (<100ms)

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

MIT License - Ver [LICENSE](../OPA_Machine/LICENSE) en repositorio supervisor.

## 🔗 Enlaces

- **Repositorio Supervisor**: [OPA_Machine](https://github.com/Ocaxtar/OPA_Machine)
- **Contratos**: [`docs/contracts/`](../OPA_Machine/docs/contracts/)
- **ADRs**: [`docs/adr/`](../OPA_Machine/docs/adr/)
- **Linear**: [Proyecto opa-quotes-streamer](https://linear.app/opa-machine/team/OPA/project/opa-quotes-streamer)
