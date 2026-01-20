# Benchmark Streaming Python - 300 Tickers

**Issue**: OPA-286
**Fecha**: 2026-01-20T12:05:17.136952
**Repositorio**: opa-quotes-streamer

---

## 📊 Resumen Ejecutivo

| Métrica | Valor | Target | Estado |
|---------|-------|--------|--------|
| Tickers | 300 | 300 | ✅ |
| Duración | 0.08h | 2h | ⚠️ |
| Latencia p99 | 39351ms | <200ms | ❌ |
| Error rate | 0.00% | <1% | ✅ |
| Gaps | 0 | <5 | ✅ |

### Pregunta Principal

> **¿Python escala a 300 tickers?** **NO**

---

## 🔢 Métricas Detalladas

### Throughput

- **Total quotes**: 867
- **Quotes/segundo**: 2.85
- **Quotes/minuto**: 170.9
- **Ciclos completados**: 3

### Latencia (ms)

| Percentil | Valor |
|-----------|-------|
| p50 | 29193.88ms |
| p95 | 39351.05ms |
| p99 | 39351.05ms |

### Recursos

| Recurso | Promedio | Máximo |
|---------|----------|--------|
| Memoria | 210.8 MB | 242.1 MB |
| CPU | 0.0% | 0.0% |

### Fiabilidad

- **Errores totales**: 0
- **Gaps detectados**: 0
- **Tasa de error**: 0.00%

---

## 🎯 Recomendación

⚠️ **Migrar a Rust** - Latencia crítica

Latencia p99 (39351ms) excede umbrales aceptables.

### Próximos pasos

1. Documentar en ADR-019 justificación para Rust
2. Evaluar timeline migración Rust
3. Actualizar OPA-289 con esta decisión

---

## 📎 Datos Crudos

```json
{
  "benchmark_id": "OPA-286",
  "timestamp": "2026-01-20T12:05:17.136952",
  "configuration": {
    "tickers_count": 300,
    "duration_seconds": 304.336077,
    "duration_hours": 0.08453779916666666,
    "polling_interval": 60
  },
  "throughput": {
    "total_quotes": 867,
    "quotes_per_second": 2.848824262133076,
    "quotes_per_minute": 170.92945572798456,
    "cycles_completed": 3
  },
  "latency_ms": {
    "p50": 29193.88,
    "p95": 39351.05,
    "p99": 39351.05,
    "samples": 3
  },
  "resources": {
    "memory_avg_mb": 210.8,
    "memory_max_mb": 242.14,
    "cpu_avg_percent": 0.0,
    "cpu_max_percent": 0.0
  },
  "reliability": {
    "errors_count": 0,
    "gaps_detected": 0,
    "error_rate_percent": 0.0
  }
}
```

---

*Generado automáticamente por `scripts/benchmark_streaming.py`*
