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

## 🔧 Gestión de Tools MCP

### Activación de Tools Linear/GitHub

Algunas herramientas MCP (Model Context Protocol) requieren activación explícita antes de usarse. **SIEMPRE** activa las tools necesarias al inicio de tu trabajo con este repositorio.

#### Tools que Requieren Activación

**Linear:**

| Grupo Linear | Tool de Activación | Cuándo Usar |
|--------------|-------------------|-------------|
| **Issues/Labels/Proyectos** | `activate_issue_management_tools()` | Crear/actualizar issues, labels, proyectos |
| **Documentos** | `activate_document_management_tools()` | Crear/actualizar documentos Linear |
| **Tracking** | `activate_issue_tracking_tools()` | Obtener status, attachments, branches |
| **Workspace** | `activate_workspace_overview_tools()` | Listar proyectos, labels, teams, users |
| **Teams/Users** | `activate_team_and_user_management_tools()` | Info de teams, users, ciclos |

**GitHub:**

| Grupo GitHub | Tool de Activación | Cuándo Usar |
|--------------|-------------------|-------------|
| **PRs Review** | `activate_pull_request_review_tools()` | Crear/revisar PRs, comentarios review |
| **Repos/Branches** | `activate_repository_management_tools()` | Crear repos, branches, PRs, merges |
| **Files** | `activate_file_management_tools()` | Eliminar/obtener archivos en GitHub |
| **Info Repos** | `activate_repository_information_tools()` | Commits, releases, tags, issues, profile |
| **Releases/Tags** | `activate_release_and_tag_management_tools()` | Listar/obtener releases y tags |
| **Search** | `activate_search_and_discovery_tools()` | Buscar código, repos, usuarios |
| **Branches/Commits** | `activate_branch_and_commit_tools()` | Listar branches, obtener commits |

**Nota**: Pylance MCP tools están siempre activas (no requieren activación).

#### Workflow de Activación

```python
# Al inicio de trabajo con Linear
<invoke name="activate_issue_management_tools" />

# Al trabajar con GitHub PRs
<invoke name="activate_repository_management_tools" />

# Al revisar PRs
<invoke name="activate_pull_request_review_tools" />
```

#### Patrón de Uso Seguro

**✅ CORRECTO**:
1. Detectar necesidad de tool (ej: crear comentario en Linear)
2. Activar categoría de tools
3. Usar tool específico

**❌ INCORRECTO**:
1. Intentar usar tool sin activar
2. Recibir error "Tool not found"
3. Continuar sin completar acción

**Ejemplo correcto**:
```markdown
- User: "Crea issue para X"
- Agent: activate_issue_management_tools() → mcp_linear_create_issue(...)
```

**Ejemplo incorrecto** ❌:
```markdown
- User: "Crea issue para X"
- Agent: mcp_linear_create_issue(...) → ERROR
- Agent: "No pude crear issue, continuando..." → ❌ VIOLACIÓN
```

#### Manejo de Errores

Si recibes `Tool not found or not activated`:
1. **NO continues** sin completar la acción
2. Activa la categoría de tools correspondiente
3. **Reintenta** la operación
4. Si persiste error, devuelve control al usuario

#### Detección de Fallo Recurrente

Si una tool falla **2+ veces** tras activar:

```markdown
⚠️ **Fallo Recurrente de Tool MCP**

He intentado usar `mcp_linear_create_issue` pero falla incluso tras activar el grupo.

**Pasos realizados**:
1. activate_issue_management_tools() ✅
2. mcp_linear_create_issue(...) ❌ Error: [error específico]
3. Reintento → ❌ Error persistente

**Solicitud**: ¿Puedes verificar permisos MCP o reportar bug?
```

### Tools Siempre Disponibles

Estas tools NO requieren activación:
- `mcp_linear_get_issue`, `mcp_linear_list_comments`, `mcp_linear_list_issues`
- `file_search`, `grep_search`, `read_file`, `replace_string_in_file`
- `run_in_terminal`, `get_terminal_output`
- Git commands via terminal

## 🛡️ Validación de Convenciones

### Checkpoint Pre-Acción

Antes de ejecutar acciones críticas, **VALIDA** que cumples las convenciones de este repositorio:

#### ✅ Pre-Commit Checklist

- [ ] **Mensaje de commit** incluye identificador de issue (ej: `OPA-232: ...`)
- [ ] **Branch** sigue convención: `oscarcalvo/OPA-XXX-descripcion-corta`
- [ ] **Tests** pasan localmente (`poetry run pytest`)
- [ ] **Linter** sin errores
- [ ] **Issue en Linear** existe y está en estado correcto

#### ✅ Pre-Issue Close Checklist

- [ ] **Comentario de cierre** añadido con prefijo `🤖 Agente opa-quotes-streamer:`
- [ ] **Pre-checks** documentados en comentario
- [ ] **Problema identificado** explicado
- [ ] **Solución implementada** detallada
- [ ] **Commits** referenciados con hash y link
- [ ] **Verificación** realizada y documentada
- [ ] **Branch mergeada** y eliminada (local + remota)

#### ✅ Pre-PR Checklist

- [ ] **Título** incluye identificador de issue
- [ ] **Descripción** explica cambios y rationale
- [ ] **Tests** incluidos para nuevas features
- [ ] **Docs** actualizadas si API cambió

### Detección de Violaciones

Si detectas que estás a punto de violar una convención:

1. **DETENTE** inmediatamente
2. **INFORMA** al usuario del problema detectado
3. **SUGIERE** corrección
4. **ESPERA** confirmación del usuario antes de continuar

**Ejemplo**:
```
⚠️ DETECCIÓN DE VIOLACIÓN

Convención: "Commits DEBEN referenciar issue Linear"
Acción planeada: git commit -m "Fix bug"
Problema: Mensaje sin identificador OPA-XXX

¿Deseas que corrija el mensaje a "OPA-232: Fix bug"?
```

### Recuperación ante Violaciones

Si ya violaste una convención:

1. **RECONOCE** el error
2. **CORRIGE** si es posible:
   - Commit sin issue: `git commit --amend -m "OPA-XXX: ..."`
   - Issue cerrado sin comentario: Añadir comentario retroactivamente
   - Branch sin mergear: `git checkout main && git merge --squash ...`
3. **DOCUMENTA** la corrección en Linear/GitHub

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
```

### 3. Workflow de Merge (OBLIGATORIO)

```bash
# 1. Asegurar que todos los cambios están commiteados
git status  # Debe estar limpio

# 2. Actualizar main local
git checkout main
git pull origin main

# 3. Mergear branch a main (squash para historia limpia)
git merge --squash oscarcalvo/OPA-194-yfinance-source

# 4. Commit final con mensaje de issue
git commit -m "OPA-194: Implementar YFinanceSource con rate limiting"

# 5. Pushear a GitHub
git push origin main

# 6. Eliminar branch local y remota
git branch -d oscarcalvo/OPA-194-yfinance-source
git push origin --delete oscarcalvo/OPA-194-yfinance-source 2>/dev/null || true

# 7. Actualizar Linear
# - Añadir comentario de cierre: "🤖 Agente opa-quotes-streamer: YFinanceSource implementado..."
# - Solo ENTONCES: Mover a "Done"
```

**⚠️ REGLA CRÍTICA**: NO cerrar issue si la branch no está mergeada. Ramas sin mergear = trabajo perdido.

### 4. Testing

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

### 5. Convenciones Linear

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

### 6. Naming Conventions

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

## Referencias

**Supervisor**:
- Arquitectura: `OPA_Machine/docs/architecture/ecosystem-overview.md`
- Contratos: `OPA_Machine/docs/contracts/data-models/quotes.md`

**Repos relacionados**:
- [opa-quotes-storage](https://github.com/Ocaxtar/opa-quotes-storage)
- [opa-quotes-api](https://github.com/Ocaxtar/opa-quotes-api)

---

📝 **Este documento debe actualizarse conforme evolucione el repositorio**  
**Última sincronización con supervisor**: 2025-12-22
