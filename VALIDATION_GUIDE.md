# Guía de Ejecución - Validación OPA-265

## Objetivo

Validar streaming de 100 tickers durante 1 hora continua con métricas operativas.

## Pre-requisitos

### 1. Servicios Dependientes

Asegúrate de tener corriendo:

```bash
# opa-quotes-storage (puerto 5001)
cd ../opa-quotes-storage
docker-compose up -d

# O si usas TimescaleDB local:
docker run -d --name timescaledb -p 5432:5432 \
  -e POSTGRES_PASSWORD=opa_password \
  timescale/timescaledb:latest-pg15
```

### 2. Variables de Entorno

Crea `.env` en la raíz del proyecto (opcional, el script usa defaults):

```env
# Database (para pipeline logging)
DATABASE_URL=postgresql://opa_user:opa_password@localhost:5432/opa_quotes

# Storage API
STORAGE_API_URL=http://localhost:5001
STORAGE_TIMEOUT=30

# Métricas
METRICS_PORT=9090
LOG_LEVEL=INFO
```

### 3. Instalar Dependencias

```bash
poetry install
```

## Ejecución

### Modo 1: Validación Completa (1 hora)

```bash
poetry run python run_validation.py
```

Esto ejecutará:
- Streaming de 100 tickers del S&P 500
- Fetch cada 60 segundos (configurable en `config/streaming.yaml`)
- Batch de 10 tickers por fetch
- Generación automática de reporte al finalizar

### Modo 2: Prueba Rápida (5 minutos)

Para validar configuración antes de ejecución larga:

```bash
# Editar config/streaming.yaml temporalmente:
# validation:
#   duration: 300  # 5 minutos

poetry run python run_validation.py
```

### Modo 3: Streaming Continuo (sin límite)

```bash
# Usar script original
poetry run python -m opa_quotes_streamer.main
```

## Monitoreo Durante Ejecución

### 1. Ver Logs en Tiempo Real

```bash
tail -f logs/streaming.log | grep -E "Cycle|quotes|error"
```

### 2. Verificar Métricas Prometheus

```bash
# Ver todas las métricas
curl http://localhost:9090/metrics | grep streamer_

# Métricas clave:
# - streamer_quotes_fetched_total
# - streamer_quotes_published_total
# - streamer_errors_total
# - streamer_fetch_duration_seconds
# - streamer_active_tickers
```

### 3. Verificar Almacenamiento

```bash
# Si opa-quotes-storage tiene endpoint de health
curl http://localhost:5001/health

# O consultar directamente en TimescaleDB
psql -h localhost -U opa_user -d opa_quotes -c \
  "SELECT COUNT(*) FROM quotes WHERE timestamp > NOW() - INTERVAL '10 minutes';"
```

## Reporte de Validación

Al finalizar, se genera:

```
logs/validation_report_YYYYMMDD_HHMMSS.json
```

**Contenido**:
```json
{
  "validation_id": "OPA-265",
  "start_time": "2026-01-16T14:00:00",
  "end_time": "2026-01-16T15:00:00",
  "duration_seconds": 3600,
  "metrics": {
    "total_quotes_fetched": 6000,
    "total_quotes_published": 5950,
    "total_cycles": 60,
    "quotes_per_minute": 99.2
  },
  "acceptance_criteria": {
    "duration_ok": true,
    "quotes_ok": true
  }
}
```

## Criterios de Aceptación

- ✅ **Duración**: ≥1 hora sin interrupciones críticas
- ✅ **Quotes totales**: >1000 quotes generadas
- ✅ **Latencia**: p95 fetch <2s (ver métricas Prometheus)
- ✅ **Rate limiting**: Sin errores de límite
- ✅ **Logs operativos**: Métricas Prometheus disponibles

## Solución de Problemas

### Error: "Connection refused" a Storage API

```bash
# Verificar que opa-quotes-storage esté corriendo
curl http://localhost:5001/health

# Si no está, iniciar:
cd ../opa-quotes-storage
docker-compose up -d
```

### Error: "Port already in use" (9090)

```bash
# Cambiar puerto en config/streaming.yaml
metrics:
  port: 9091

# O detener servicio conflictivo
lsof -ti:9090 | xargs kill -9
```

### Pocos Quotes Generados

Causas comunes:
1. **Yahoo Finance rate limiting**: Aumentar `fetch_interval` a 90s
2. **Errores de red**: Ver logs con `grep error logs/streaming.log`
3. **Storage API caído**: Circuit breaker abrirá, ver métricas

### Validar Sin Storage API (modo standalone)

Modificar `config/streaming.yaml`:

```yaml
publishers:
  storage:
    enabled: false  # Desactivar publicación
```

Quotes se fetchearán pero no se publicarán (útil para testing de source).

## Estructura de Archivos Generados

```
logs/
├── streaming.log                        # Log principal
├── validation_report_20260116_140000.json  # Reporte de validación
└── prometheus/                          # (Si se configura file export)
```

## Referencias

- **Issue**: [OPA-265](https://linear.app/opa-machine/issue/OPA-265)
- **Config**: [config/streaming.yaml](config/streaming.yaml)
- **Tickers**: Lista en `OPA_Machine/docs/data-references/sp500-top100-liquid.md`
- **Contratos**: `OPA_Machine/docs/contracts/events/quotes-stream.md`

---

**Última actualización**: 2026-01-16  
**Mantenido por**: Agente opa-quotes-streamer
