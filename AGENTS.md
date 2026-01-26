# AGENTS.md - opa-quotes-streamer

> 🎯 **Guía específica para agentes IA** en este repo operativo.  
> **Supervisión**: [OPA_Machine/AGENTS.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/AGENTS.md)

---

## 🚦 Pre-Flight Checklist (OBLIGATORIO)

| Acción | Documento/Skill | Cuándo |
|--------|-----------------|--------|
| Consultar infraestructura | [opa-infrastructure-state](https://github.com/Ocaxtar/opa-infrastructure-state/blob/main/state.yaml) | ANTES de Docker/DB/Redis |
| Sincronizar workspace | Skill `workspace-sync` (supervisor) | Inicio sesión |
| Verificar estado repos | [DASHBOARD.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/DASHBOARD.md) | Inicio sesión |
| Trabajar en issue | Skill `git-linear-workflow` | Antes branch/commit |
| Usar Linear MCP | Skill `linear-mcp-tool` | Si tool falla/UUID |

---

## 📋 Info del Repositorio

**Nombre**: opa-quotes-streamer  
**Tipo**: Streamer (Rust)  
**Propósito**: Recolección streaming de ~300 tickers desde fuentes públicas (Polygon.io, Alpha Vantage)  
**Puerto**: Ninguno (background service)  
**Team Linear**: OPA  
**Tecnologías**: Rust 1.74, Tokio (async runtime), Redis (pub/sub), PostgreSQL (escritura directa)

**Funcionalidad**:
- WebSocket connections a múltiples providers
- Procesamiento concurrente (300+ streams simultáneos)
- Escritura a Redis (canal `quotes:stream`) para real-time
- Escritura a PostgreSQL (opa-quotes-storage) para históricos
- Backpressure management y reconexión automática

**Dependencias**:
- opa-quotes-storage (PostgreSQL escritura en puerto 5433)
- Redis (pub/sub canal `quotes:stream`)

---

## 🎯 Skills Disponibles (carga bajo demanda)

| Skill | Ubicación | Triggers |
|-------|-----------|----------|
| `git-linear-workflow` | `~/.copilot/skills/` | issue, branch, commit, PR |
| `linear-mcp-tool` | `~/.copilot/skills/` | error Linear, UUID |
| `run-efficiency` | `~/.copilot/skills/` | tokens, context |

**Skills supervisor** (consultar desde [supervisor](https://github.com/Ocaxtar/OPA_Machine)):
- `multi-workspace`, `contract-validator`, `ecosystem-auditor`, `infrastructure-lookup`

---

## 🔄 Workflows Especiales

### Schemas DB del Ecosistema (OPA-343)

**Nota**: Este repo (Rust) no crea SQLAlchemy models, pero para contexto:

El ecosistema usa [state-db-schemas.yaml.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/infrastructure/state-db-schemas.yaml.md) como **source of truth** de schemas DB reales.

**Tablas del módulo Quotes**:
- `quotes.quotes` - Almacenado en opa-quotes-storage (TimescaleDB)
- Este streamer escribe via conexión PostgreSQL directa (no ORM)

---

## 🛠️ Gestión de MCP Tools

### Activar Grupos de Herramientas

```
❌ Llamar mcp_github-* sin activar
✅ SIEMPRE activar grupo antes:
    1. activate_repository_management_tools()
    2. LUEGO mcp_github-mcp_create_branch(...)
```

**Grupos disponibles**:
- `activate_repository_management_tools()` - branches, PRs, repos
- `activate_pull_request_review_tools()` - reviews, comments
- `activate_repository_information_tools()` - commits, releases, issues
- `activate_search_and_discovery_tools()` - búsqueda código/repos

---

## ✅ Validación Pre-Done de Issues

### Antes de Cerrar Issues en Linear

**OBLIGATORIO** verificar:

1. **Cambios en main**:
   ```bash
   git log origin/main --oneline -5
   # Verificar tu commit está en main
   ```

2. **CI/CD pasó**:
   - GitHub Actions: ✅ All checks passed
   - Si hay fallos, NO cerrar hasta resolverlos

3. **Criterios de aceptación**:
   - Revisar checklist en descripción issue
   - Marcar todos los `[ ]` → `[x]`

4. **Actualizar Linear con resumen**:
   ```python
   mcp_linear_create_comment(
       issueId="uuid",
       body="## ✅ Completado\n- Cambios en main: hash\n- CI pasó: ✅"
   )
   ```

5. **SOLO ENTONCES** cerrar:
   ```python
   mcp_linear_update_issue(id="uuid", state="Done")
   ```

---

## ⚠️ Reglas Críticas Específicas

### 1. Puerto PostgreSQL = 5433 (NO 5432)

```rust
// ❌ Incorrecto
let db_url = "postgresql://localhost:5432/opa_quotes";

// ✅ Correcto
let db_url = "postgresql://localhost:5433/opa_quotes";
```

**Motivo**: Windows local ocupa 5432. Ver [service-inventory.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/infrastructure/service-inventory.md).

### 2. Backpressure para escritura PostgreSQL

```rust
// ✅ Patrón obligatorio
let (tx, mut rx) = mpsc::channel::<Quote>(1000);

tokio::spawn(async move {
    while let Some(quote) = rx.recv().await {
        // Batch de 100 quotes o timeout de 5s
        let batch = collect_batch(&mut rx, 100, Duration::from_secs(5)).await;
        db.batch_insert(batch).await;
    }
});
```

**Motivo**: 300 streams → 900 quotes/sec → sin batching se satura PostgreSQL.

### 3. Escritura dual (Redis + PostgreSQL)

```rust
// ✅ Correcto: Redis primero (no bloqueante), PostgreSQL después
redis_client.publish("quotes:stream", &quote).await?;
db_tx.send(quote).await?;  // Canal async → batch worker
```

**Orden**: Redis es crítico (real-time), PostgreSQL es secondary (históricos).

---

## 🔧 Operaciones de Infraestructura

> **OBLIGATORIO**: Ejecutar ANTES de cualquier operación Docker/DB/Redis.

### Workflow de 3 Pasos

#### Paso 1: Ejecutar Preflight Check

```bash
# Desde este repo
python ../opa-supervisor/scripts/infrastructure/preflight_check.py --module quotes --operation docker-compose
```

#### Paso 2: Evaluar Resultado

| Resultado | Acción |
|-----------|--------|
| ✅ PREFLIGHT PASSED | Continuar con la tarea |
| ❌ PREFLIGHT FAILED | **NO continuar**. Reportar al usuario qué servicios faltan |

#### Paso 3: Configurar usando state.yaml

**Source of Truth**: `opa-infrastructure-state/state.yaml`

```rust
// ✅ CORRECTO: Leer de variables de entorno
let db_url = std::env::var("DATABASE_URL")
    .unwrap_or_else(|_| "postgresql://opa_user:opa_password@localhost:5433/opa_quotes".to_string());

// ❌ INCORRECTO: Hardcodear valores
let db_url = "postgresql://opa_user:opa_password@localhost:5433/opa_quotes";
```

### Anti-Patrones (PROHIBIDO)

| Anti-Patrón | Por qué está mal |
|-------------|------------------|
| ❌ Consultar `service-inventory.md` como fuente | Es documento AUTO-GENERADO, no editable |
| ❌ Hardcodear puertos/credenciales | Dificulta mantenimiento y causa bugs |
| ❌ Asumir que servicio existe sin validar | Causa "Connection refused" en deploy |
| ❌ Usar puerto 5432 para Docker | PostgreSQL local Windows lo ocupa |
| ❌ Continuar si preflight falla | Propaga configuración inválida |

### Quick Reference: Puertos

| Servicio | Puerto | Módulo |
|----------|--------|--------|
| TimescaleDB Quotes | 5433 | Quotes |
| TimescaleDB Capacity | 5434 | Capacity |
| Redis Dev | 6381 | Shared |
| quotes-api | 8000 | Quotes |
| capacity-api | 8001 | Capacity |

> **Source of Truth**: [opa-infrastructure-state/state.yaml](https://github.com/Ocaxtar/opa-infrastructure-state/blob/main/state.yaml)

---

## 🔧 Convenciones

| Elemento | Convención |
|----------|------------|
| **Idioma código** | Inglés |
| **Idioma interacción** | Español |
| **Formato commit** | `OPA-XXX: Descripción imperativa` |
| **Branches** | `username/opa-xxx-descripcion` |
| **Labels issues** | `Feature/Bug` + `opa-quotes-streamer` |
| **Rust edition** | 2021 |
| **MSRV** | 1.74.0 |

---

## 📚 Referencias

| Recurso | URL |
|---------|-----|
| Supervisor AGENTS.md | https://github.com/Ocaxtar/OPA_Machine/blob/main/AGENTS.md |
| opa-infrastructure-state | https://github.com/Ocaxtar/opa-infrastructure-state/blob/main/state.yaml |
| DB Schemas Source of Truth | https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/infrastructure/state-db-schemas.yaml.md |
| Service Inventory | https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/infrastructure/service-inventory.md |
| DASHBOARD | https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/DASHBOARD.md |

---

*Documento sincronizado con supervisor v2.1 (2026-01-26) - OPA-370*
