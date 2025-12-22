# AGENTS.md - Guía para Agentes IA (opa-quotes-streamer)

## Información del Repositorio

**Nombre**: opa-quotes-streamer  
**Módulo**: Módulo 5 (Cotización)  
**Tipo**: Servicio de streaming en tiempo real  
**Fase**: 1 (Python) → 2 (Rust migration)  
**Workspace**: `opa-quotes-streamer` (autónomo)  
**Proyecto Linear**: opa-quotes-streamer  
**Label Linear**: `opa-quotes-streamer`

## Contexto del Servicio

Este servicio es el **ingestion layer** del Módulo 5 (Cotización). Responsable de:

1. Conectar con fuentes de datos financieros (yfinance en Fase 1)
2. Streaming continuo de cotizaciones para 10-50 tickers
3. Normalización a schema estándar (ver contratos)
4. Envío a `opa-quotes-storage` mediante HTTP batching
5. Resiliencia ante fallos (circuit breaker, exponential backoff)

### Arquitectura del Módulo 5

```
yfinance API → opa-quotes-streamer → opa-quotes-storage → opa-quotes-api
                     │                        │
                     └──── Métricas ──────────┘
                         (Prometheus)
```

### Responsabilidades del Agente

- **NO modificar otros repositorios**: Este agente solo trabaja en `opa-quotes-streamer`
- **Consultar contratos**: Leer `docs/contracts/data-models/quotes.md` del supervisor antes de cambiar schemas
- **Crear issues en Linear**: Solo en proyecto `opa-quotes-streamer`, label `opa-quotes-streamer`
- **Commits con prefijo**: `OPA-XXX: Descripción` (XXX = número de issue Linear)

## Stack Tecnológico (Fase 1)

### Lenguaje y Runtime

| Componente | Versión | Rationale |
|------------|---------|-----------|
| **Python** | 3.12 | Async/await para streaming, ecosistema maduro |
| **asyncio** | stdlib | Event loop para concurrencia I/O-bound |
| **Poetry** | 1.7+ | Gestión de dependencias |

### Bibliotecas Core

| Biblioteca | Versión | Propósito | Cuando Usar |
|------------|---------|-----------|-------------|
| **yfinance** | 0.2.32+ | Data source (Yahoo Finance) | Fetch quotes en Fase 1 |
| **aiohttp** | 3.9+ | Async HTTP client | Fetch desde APIs externas |
| **websockets** | 12.0+ | WebSocket streaming | Fase 2 (real-time sources) |
| **pandas** | 2.1+ | Data manipulation | Transformación de quotes |
| **Pydantic** | 2.5+ | Schema validation | Quote models, config |
| **httpx** | 0.25+ | HTTP client | POST a opa-quotes-storage |

### Infraestructura

| Componente | Versión | Propósito |
|------------|---------|-----------|
| **Docker Compose** | 2.23+ | Orquestación local |
| **Prometheus** | latest | Métricas |
| **GitHub Actions** | - | CI/CD (lint + tests) |

## Arquitectura del Servicio

### Capas (Onion Architecture)

```
StreamingService (main.py)
    ↓
DataSource Layer (sources/)
    ├── BaseDataSource (interface)
    ├── YFinanceSource (Fase 1 implementation)
    └── IEXCloudSource (Fase 2 future)
    ↓
Publisher Layer (publishers/)
    ├── BasePublisher (interface)
    └── StoragePublisher (HTTP → opa-quotes-storage)
    ↓
Utils Layer
    ├── RateLimiter (token bucket)
    ├── CircuitBreaker (resiliency)
    └── PipelineLogger (structured logging)
```

### Flujo de Datos

```python
# 1. Fetch quotes desde yfinance (async)
quotes: List[Quote] = await yfinance_source.fetch_quotes(tickers)

# 2. Validar con Pydantic
validated_quotes = [Quote.model_validate(q) for q in quotes]

# 3. Batch publish a storage
await storage_publisher.publish_batch(validated_quotes)

# 4. Log métricas
pipeline_logger.log_metrics(quotes_count=len(quotes))
```

### Estrategia de Rate Limiting

**yfinance API límites** (gratuito):
- ~2000 requests/hora
- ~1 request cada 1.8s

**Implementación**:
```python
# utils/rate_limiter.py
class RateLimiter:
    def __init__(self, max_requests_per_hour: int):
        self.tokens = max_requests_per_hour
        self.refill_rate = max_requests_per_hour / 3600  # Por segundo
    
    async def acquire(self):
        while self.tokens < 1:
            await asyncio.sleep(1)
        self.tokens -= 1
```

**Uso**:
```python
rate_limiter = RateLimiter(max_requests_per_hour=2000)

async def fetch_quotes():
    await rate_limiter.acquire()  # Espera token
    quotes = await yfinance.download(tickers)
    return quotes
```

### Circuit Breaker Pattern

**Propósito**: Prevenir cascading failures si `opa-quotes-storage` está caído.

**Estados**:
- **CLOSED**: Operación normal
- **OPEN**: Storage falló >5 veces, no intentar durante 60s
- **HALF_OPEN**: Probar 1 request tras cooldown

**Implementación**:
```python
# utils/circuit_breaker.py
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.state = "CLOSED"
        self.failures = 0
        self.last_failure_time = None
    
    async def call(self, func):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time < self.timeout:
                raise CircuitBreakerOpenError()
            self.state = "HALF_OPEN"
        
        try:
            result = await func()
            self.failures = 0
            self.state = "CLOSED"
            return result
        except Exception as e:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                self.last_failure_time = time.time()
            raise
```

## Workflow de Desarrollo

### 1. Setup Inicial

```bash
# Clonar repo
git clone https://github.com/Ocaxtar/opa-quotes-streamer.git
cd opa-quotes-streamer

# Instalar dependencias
poetry install

# Configurar entorno
cp .env.example .env
# Editar TICKERS, POLLING_INTERVAL, STORAGE_API_URL

# Verificar instalación
poetry run pytest tests/unit -v
```

### 2. Implementar Feature

**Ejemplo**: Implementar `YFinanceSource`

```bash
# 1. Crear issue en Linear
# Título: "Implementar YFinanceSource con rate limiting"
# Label: opa-quotes-streamer
# Prioridad: High
# ID obtenido: OPA-194

# 2. Crear branch
git checkout -b oscarcalvo/OPA-194-yfinance-source

# 3. Implementar
# src/opa_quotes_streamer/sources/yfinance_source.py
from opa_quotes_streamer.sources.base import BaseDataSource
from opa_quotes_streamer.models.quote import Quote
import yfinance as yf

class YFinanceSource(BaseDataSource):
    async def fetch_quotes(self, tickers: List[str]) -> List[Quote]:
        # Implementación con rate limiting
        pass

# 4. Tests
# tests/unit/test_yfinance_source.py
@pytest.mark.asyncio
async def test_fetch_quotes_success():
    source = YFinanceSource(tickers=["AAPL"])
    quotes = await source.fetch_quotes()
    assert len(quotes) == 1

# 5. Ejecutar tests
poetry run pytest tests/unit/test_yfinance_source.py -v

# 6. Commit
git add src/ tests/
git commit -m "OPA-194: Implementar YFinanceSource con rate limiting

- Clase YFinanceSource hereda de BaseDataSource
- Rate limiter integrado (2000 req/h)
- Manejo de errores con retry exponencial
- Tests unitarios con mocks

Tests: 5 OK, 0 failures"

# 7. Push
git push origin oscarcalvo/OPA-194-yfinance-source

# 8. Actualizar Linear
# Comentario: "🤖 Agente opa-quotes-streamer: YFinanceSource implementado..."
# Estado: Done

# 9. Merge a main
git checkout main
git pull origin main
git merge oscarcalvo/OPA-194-yfinance-source --no-ff
git push origin main

# 10. Eliminar branch (opcional)
git branch -d oscarcalvo/OPA-194-yfinance-source
git push origin --delete oscarcalvo/OPA-194-yfinance-source
```

**IMPORTANTE**: Siempre hacer merge a `main` al completar una issue antes de comenzar la siguiente.

### 3. Testing

#### Tests Unitarios (con mocks)

```python
# tests/unit/test_yfinance_source.py
import pytest
from unittest.mock import AsyncMock, patch
from opa_quotes_streamer.sources.yfinance_source import YFinanceSource

@pytest.mark.asyncio
async def test_fetch_quotes_with_rate_limit():
    with patch('yfinance.download') as mock_download:
        mock_download.return_value = [
            {"ticker": "AAPL", "price": 178.45}
        ]
        
        source = YFinanceSource(tickers=["AAPL"])
        quotes = await source.fetch_quotes()
        
        assert len(quotes) == 1
        assert quotes[0].ticker == "AAPL"
        mock_download.assert_called_once()
```

#### Tests de Integración (con servicios reales)

```python
# tests/integration/test_streaming_pipeline.py
import pytest
from opa_quotes_streamer.main import StreamingService

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_streaming_pipeline():
    # Requiere docker-compose up (opa-quotes-storage mock)
    service = StreamingService(tickers=["AAPL"], polling_interval=1)
    
    await service.start()
    await asyncio.sleep(5)  # Stream por 5s
    await service.stop()
    
    # Verificar que se enviaron quotes a storage
    # (requiere mock HTTP server o storage real)
```

#### Ejecutar Tests

```bash
# Solo unitarios (rápidos)
poetry run pytest tests/unit -v

# Solo integración (lentos, requiere docker)
poetry run pytest tests/integration -v

# Con coverage
poetry run pytest --cov=opa_quotes_streamer --cov-report=html

# Test específico
poetry run pytest tests/unit/test_yfinance_source.py::test_fetch_quotes_success -v
```

### 4. Convenciones Linear

#### Crear Issue

```python
# Usar MCP Linear
mcp_linear_create_issue(
    team="opa-quotes-streamer",
    title="Implementar YFinanceSource con rate limiting",
    description="""
## Objetivo
Crear clase YFinanceSource que fetch quotes desde Yahoo Finance.

## Tareas
- [ ] Implementar BaseDataSource interface
- [ ] Integrar RateLimiter (2000 req/h)
- [ ] Manejo de errores con retry
- [ ] Tests unitarios con mocks

## Criterios de Aceptación
- [ ] Fetch 10 tickers en <2s
- [ ] Rate limiting respetado
- [ ] Tests: 100% coverage
    """,
    labels=["opa-quotes-streamer", "Feature"],
    priority=2  # High
)
```

#### Comentario de Cierre

**Template obligatorio**:

```markdown
🤖 Agente opa-quotes-streamer: Issue resuelta exitosamente

## ✅ Pre-checks
- [x] Leídos TODOS los comentarios de la issue
- [x] Verificadas dependencias mencionadas
- [x] No hay instrucciones contradictorias pendientes

## 🔧 Cambios Realizados
- Implementado YFinanceSource en `src/opa_quotes_streamer/sources/yfinance_source.py`
- Rate limiter integrado (token bucket, 2000 req/h)
- Manejo de errores con exponential backoff (1s, 2s, 4s)
- Tests unitarios: 5 tests, 100% coverage

## 📦 Commits
- Commit: [abc1234](https://github.com/Ocaxtar/opa-quotes-streamer/commit/abc1234)
- Mensaje: "OPA-194: Implementar YFinanceSource con rate limiting"

## 🧪 Verificación
```bash
poetry run pytest tests/unit/test_yfinance_source.py -v
# Output: 5 passed, 0 failed
```

## ✅ Criterios de Aceptación Cumplidos
- [x] Fetch 10 tickers en <2s
- [x] Rate limiting respetado
- [x] Tests: 100% coverage

Issue cerrada.
```

### 5. Naming Conventions

#### Archivos y Módulos

```
✅ Correcto:
- yfinance_source.py
- storage_publisher.py
- rate_limiter.py

❌ Incorrecto:
- YFinanceSource.py (CamelCase en archivo)
- storagePublisher.py (mixedCase)
```

#### Clases

```python
✅ Correcto:
class YFinanceSource:
    pass

class StoragePublisher:
    pass

❌ Incorrecto:
class yfinance_source:  # snake_case
    pass
```

#### Funciones y Variables

```python
✅ Correcto:
async def fetch_quotes(tickers: List[str]):
    polling_interval = 5
    max_retries = 3

❌ Incorrecto:
async def FetchQuotes(tickers):  # CamelCase
    PollingInterval = 5  # CamelCase
```

## Contratos de Integración

### Upstream: yfinance API

**No hay contrato formal** (API pública de terceros).

**Schema esperado** (yfinance.download):
```python
{
    "Open": 175.23,
    "High": 178.90,
    "Low": 174.50,
    "Close": 178.45,  # Mapeado a Quote.price
    "Volume": 52341000,
    "Adj Close": 178.45
}
```

**Transformación**:
```python
def yfinance_to_quote(ticker: str, data: dict) -> Quote:
    return Quote(
        ticker=ticker,
        price=data["Close"],
        volume=data["Volume"],
        timestamp=datetime.utcnow(),
        source="yfinance"
    )
```

### Downstream: opa-quotes-storage

**Contrato**: `docs/contracts/apis/quotes-storage-api.md` (supervisor)

**Endpoint**: `POST /quotes/batch`

**Request**:
```json
{
  "quotes": [
    {
      "ticker": "AAPL",
      "price": 178.45,
      "volume": 52341000,
      "timestamp": "2025-12-22T15:30:00Z",
      "source": "yfinance"
    }
  ]
}
```

**Response**:
```json
{
  "inserted": 10,
  "errors": 0
}
```

**Cliente HTTP**:
```python
# publishers/storage_publisher.py
async def publish_batch(self, quotes: List[Quote]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.storage_url}/quotes/batch",
            json={"quotes": [q.model_dump() for q in quotes]}
        )
        response.raise_for_status()
        return response.json()
```

## Troubleshooting

### Error: "Rate limit exceeded"

**Síntoma**: Logs muestran `RateLimitError`, yfinance devuelve HTTP 429

**Diagnóstico**:
```bash
# Ver métricas Prometheus
curl http://localhost:8001/metrics | grep rate_limit_hits

# Ver logs
docker-compose logs -f streamer | grep "rate_limit"
```

**Solución**:
```bash
# Aumentar intervalo en .env
POLLING_INTERVAL=10  # De 5s a 10s

# Reducir tickers
TICKERS=AAPL,MSFT,GOOGL  # De 10 a 3

# Verificar MAX_REQUESTS_PER_HOUR
MAX_REQUESTS_PER_HOUR=2000  # Default de yfinance
```

### Error: "Connection refused to storage"

**Síntoma**: `StoragePublisher` falla con `ConnectionRefusedError`

**Diagnóstico**:
```bash
# Verificar storage está corriendo
curl http://localhost:8000/health

# Verificar red Docker
docker network ls
docker network inspect opa-quotes-streamer_default
```

**Solución**:
```bash
# En docker-compose.yml, verificar networks
services:
  streamer:
    networks:
      - opa-network
  storage:
    networks:
      - opa-network

# Reiniciar compose
docker-compose down
docker-compose up -d
```

### Tests fallan con "Event loop is closed"

**Síntoma**: Tests asyncio fallan con error de event loop

**Solución**:
```python
# Añadir fixture en conftest.py
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

## Métricas y Observabilidad

### Métricas Prometheus

**Expuestas en** `http://localhost:8001/metrics`

```python
# main.py
from prometheus_client import Counter, Histogram, Gauge

quotes_fetched = Counter('streamer_quotes_fetched_total', 'Total quotes fetched')
quotes_published = Counter('streamer_quotes_published_total', 'Total quotes published')
fetch_duration = Histogram('streamer_fetch_duration_seconds', 'Fetch latency')
active_tickers = Gauge('streamer_active_tickers', 'Active tickers count')
errors_total = Counter('streamer_errors_total', 'Errors by type', ['type'])

# Uso
quotes_fetched.inc(len(quotes))
with fetch_duration.time():
    quotes = await yfinance_source.fetch_quotes()
```

### PipelineLogger

**Propósito**: Logging estructurado con contexto de pipeline

```python
from shared.utils.pipeline_logger import PipelineLogger

pipeline_logger = PipelineLogger(
    pipeline_name="opa-quotes-streamer",
    repository="opa-quotes-streamer"
)

# Inicio
pipeline_logger.start(metadata={"tickers": 10, "interval": 5})

# Durante ejecución
logger.info(f"Fetched {len(quotes)} quotes", extra={
    "tickers": [q.ticker for q in quotes],
    "latency": 1.2
})

# Finalización
pipeline_logger.complete(
    status="success",
    output_records=100,
    metadata={"avg_latency": 1.5}
)
```

## Guía de Migración Rust (Fase 2)

**Objetivo**: Migrar a Rust para ultra-low latency (<100ms) y 1000+ tickers concurrentes.

### Stack Rust

| Crate | Versión | Propósito |
|-------|---------|-----------|
| **tokio** | 1.35+ | Async runtime |
| **tungstenite** | 0.21+ | WebSocket client |
| **reqwest** | 0.11+ | HTTP client |
| **serde** | 1.0+ | Serialization |
| **serde_json** | 1.0+ | JSON parsing |

### Estructura

```
src/
├── main.rs                  # Entry point
├── sources/
│   ├── mod.rs
│   ├── base.rs              # DataSource trait
│   └── iex_cloud.rs         # IEX Cloud WebSocket
├── publishers/
│   ├── mod.rs
│   └── storage.rs           # HTTP client to storage
└── utils/
    ├── rate_limiter.rs
    └── circuit_breaker.rs
```

### Ejemplo: IEX Cloud WebSocket

```rust
// sources/iex_cloud.rs
use tokio_tungstenite::connect_async;
use serde::Deserialize;

#[derive(Deserialize)]
struct IEXQuote {
    symbol: String,
    price: f64,
    volume: u64,
}

pub async fn stream_quotes(tickers: Vec<String>) -> Result<(), Box<dyn Error>> {
    let url = "wss://ws-api.iextrading.com/1.0/tops";
    let (ws_stream, _) = connect_async(url).await?;
    
    while let Some(msg) = ws_stream.next().await {
        let quote: IEXQuote = serde_json::from_str(&msg?)?;
        // Publish to storage
    }
    
    Ok(())
}
```

### Plan de Migración

1. **Fase 2a** (Python + Rust POC): Rust streamer en paralelo, comparar métricas
2. **Fase 2b** (Rust mayoritario): Rust 80%, Python 20% (legacy tickers)
3. **Fase 2c** (Rust completo): Deprecar Python, solo Rust

## Referencias

- **Repositorio Supervisor**: [OPA_Machine](https://github.com/Ocaxtar/OPA_Machine)
- **Contratos**: [`docs/contracts/data-models/quotes.md`](../OPA_Machine/docs/contracts/data-models/quotes.md)
- **ADR-009**: Secuenciación de fases (Python → Rust)
- **Linear**: [Proyecto opa-quotes-streamer](https://linear.app/opa-machine/team/OPA/project/opa-quotes-streamer)

---

📝 **Este documento debe actualizarse conforme evolucione el servicio**
