# ECOSYSTEM_CONTEXT.md - opa-quotes-streamer

## Posición en el Ecosistema

Este servicio es el **ingestion layer** del **Módulo 5 (Cotización)**, responsable de la conexión con fuentes de datos financieros (yfinance) y streaming continuo de cotizaciones.

```
                            ┌─────────────────────────────────────┐
                            │       OPA_Machine (Supervisor)      │
                            │  Documentación, ADRs, Contratos     │
                            └──────────────────┬──────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
         ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
         │  Módulo 1        │       │  Módulo 5        │       │  Módulo 4        │
         │  Capacidad       │       │  Cotización      │       │  Predicción      │
         └──────────────────┘       └────────┬─────────┘       └──────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
         ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
         │ quotes-streamer  │────▶│  quotes-storage  │────▶│   quotes-api     │
         │  ★ ESTE REPO ★   │     │  (downstream)    │     │  (downstream)    │
         └──────────────────┘     └──────────────────┘     └──────────────────┘
               yfinance                TimescaleDB              FastAPI REST
```

## Flujo de Datos

1. **Entrada** (desde fuentes externas):
   - yfinance API (Fase 1)
   - IEX Cloud, Alpha Vantage (Fase 2+)
   - WebSocket feeds (Fase 3: Rust migration)

2. **Procesamiento**:
   - Rate limiting (2000 req/hora yfinance)
   - Normalización a schema estándar Quote
   - Validación con Pydantic v2
   - Circuit breaker para resiliencia

3. **Salida** (hacia `opa-quotes-storage`):
   - HTTP POST batch: `POST /v1/quotes/batch`
   - Formato: JSON array de quotes normalizadas
   - Contrato: `quotes-batch.md`

## Dependencias

### Upstream (fuentes de datos)
| Fuente | Tipo | Descripción |
|--------|------|-------------|
| yfinance | HTTP | Yahoo Finance API wrapper (Fase 1) |
| IEX Cloud | REST API | Premium data (Fase 2+) |

### Downstream (consumidores)
| Servicio | Tipo | Descripción |
|----------|------|-------------|
| `opa-quotes-storage` | HTTP POST | Recibe batches para persistencia |

## Contratos Relevantes

- **Batch Endpoint**: `OPA_Machine/docs/contracts/apis/quotes/quotes-batch.md`
- **Modelo Quote**: `OPA_Machine/docs/contracts/data-models/quotes.md`
- **Invariantes**: INV-001 a INV-006 (batch size, ticker format, timestamps)

## Repositorio Supervisor

**URL**: https://github.com/Ocaxtar/OPA_Machine

Consultar para:
- ADRs globales (`docs/adr/`)
- Contratos actualizados (`docs/contracts/`)
- Guías de desarrollo (`docs/guides/`)
- ROADMAP global (`ROADMAP.md`)

---

📝 **Última sincronización con supervisor**: 2026-01-13
