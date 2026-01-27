# AGENTS.md - Guía para Agentes de IA (opa-quotes-streamer)

## Identidad y Misión

**Nombre**: Agente de Streaming de Cotizaciones (Módulo 5)
**Workspace**: `opa-quotes-streamer`
**Repositorio**: `opa-quotes-streamer`
**Rol**: Ingesta en tiempo real de cotizaciones desde múltiples fuentes (Yahoo Finance, APIs institucionales)
**Stack**: Python 3.12, asyncio, yfinance, SQLAlchemy, Redis

> **Nota**: El stack es Python 3.12 según **ADR-019** (2026-01-20) del supervisor OPA_Machine. Migración a Rust planificada para Fase 3+ (1000+ tickers). Ver [ROADMAP.md](ROADMAP.md) línea 72.

### Objetivo Principal
Implementar y operar pipelines de streaming de alta frecuencia (300 tickers Fase 2, <500ms latency por ADR-019) con circuit breakers, backpressure y recovery automático. Este servicio alimenta a `opa-quotes-storage` con datos en tiempo real.

### Documentación Base (Lectura Obligatoria)
1. **[ECOSYSTEM_CONTEXT.md](docs/ECOSYSTEM_CONTEXT.md)**: Posición en arquitectura global
2. **[DEVELOPMENT.md](docs/DEVELOPMENT.md)**: Setup técnico, testing y estándares
3. **[ROADMAP.md](ROADMAP.md)**: Objetivos Fase 1 (Cotización 40%)

### Principios de Operación
1. **Respeto Absoluto a los Contratos**: Consultar `docs/contracts/events/quotes-stream.md`
2. **Resiliencia**: Circuit breakers ante fallos de fuentes externas
3. **Performance**: Procesamiento asíncrono con asyncio, sin bloqueos
4. **Etiquetado Estricto**: Solo trabajar en issues con label `opa-quotes-streamer`

---

## 🚦 Pre-Flight Checklist (OBLIGATORIO)

**Antes de cualquier operación, verificar**:

| Acción | Documento/Skill | Cuándo |
|--------|-----------------|--------|
| 🔄 **Sincronizar workspace** | Script `scripts/git/check_sync.sh` (incluye activación MCP) | ⚠️ **INICIO DE CADA RUN** |
| Consultar infraestructura | [opa-infrastructure-state](https://github.com/Ocaxtar/opa-infrastructure-state) | ⚠️ **ANTES** de Docker/DB/Redis |
| Operar Docker/conexiones | Ver [service-inventory.md](https://github.com/Ocaxtar/opa-supervisor/blob/main/docs/infrastructure/service-inventory.md) | ⚠️ **SIEMPRE** antes de Docker |
| Trabajar en issue | Skill global `git-linear-workflow` | Antes de branch/commit |
| Usar Linear MCP tools | Skill global `linear-mcp-tool` | Si tool falla/necesitas categorías extra |

### Sincronización Automática

**Al inicio de cada run, ejecutar**:
```bash
bash scripts/git/check_sync.sh
```

**Exit codes**:
- `0`: ✅ Sincronizado (continuar)
- `2`: ⚠️ Commits locales sin push (avisar usuario)
- `3`: ⚠️ Cambios remotos en código (avisar usuario)
- `4`: ❌ Divergencia detectada (requerir resolución manual)
- `5`: ⚠️ No se pudo conectar con remoto

**Pull automático**: Si solo hay cambios en `docs/`, `AGENTS.md`, `README.md`, `ROADMAP.md` → pull automático aplicado.

**Activación MCP incluida**: El skill `workspace-sync` del supervisor OPA_Machine activa automáticamente los grupos principales de MCP tools (Linear Issues, Workspace Overview, GitHub Repos, GitHub Issues). Si necesitas tools de categorías adicionales (documentos, tracking, team management, PR reviews), actívalas bajo demanda.

**Ver detalles completos**: Consultar skill `workspace-sync` en opa-supervisor.

---

## 📚 Skills Disponibles

**Skills Globales** (ubicación: `~/.copilot/skills/`):

| Skill | Propósito |
|-------|-----------|
| `git-linear-workflow` | Workflow Git+Linear completo |
| `linear-mcp-tool` | Errores MCP Linear y soluciones |
| `run-efficiency` | Gestión tokens, pre-Done checklist |

> ⚠️ **Nota**: Skills ya no tienen carpeta local `.github/skills/`. Están centralizados en ubicación global del usuario.

**Skills OPA específicos**: Ver [opa-supervisor/.github/skills/](https://github.com/Ocaxtar/opa-supervisor/tree/main/.github/skills) para skills de arquitectura, auditoría y transición de fases.

**Guías de referencia** (supervisor):
- **[code-conventions.md](https://github.com/Ocaxtar/opa-supervisor/blob/main/docs/guides/code-conventions.md)**: Estándares código, testing, CI/CD
- **[technology-stack.md](https://github.com/Ocaxtar/opa-supervisor/blob/main/docs/guides/technology-stack.md)**: Stack tecnológico consolidado

**Convención idiomática**:
- **Código y nombres técnicos** (clases, funciones, commits): **Inglés**
- **Interacción con usuarios** (comentarios Linear, PRs, docs narrativa): **Español**

---

## 🔧 Gestión de Tools MCP (Linear, GitHub)

**REGLA CRÍTICA**: Muchas tools de Linear/GitHub requieren activación explícita antes de uso.

### Workflow de Activación

Si intentas usar una tool y fallas con:
```
Tool mcp_linear_create_issue is currently disabled by the user, and cannot be called.
ERROR: Tool not found or not activated
```

**NO continúes sin la tool**. Debes:
1. ✅ Activar el grupo de tools correspondiente
2. ✅ Reintentar la operación original
3. ❌ NUNCA saltar el paso o usar alternativa

### Grupos de Tools Disponibles

**Linear** (usar `activate_*_tools`):
- `activate_issue_management_tools`: create_issue, update_issue, create_comment, create_label, create_project
- `activate_workspace_overview_tools`: list_projects, list_documents, list_labels, list_teams, list_users
- `activate_team_and_user_management_tools`: get_team, get_user, get_cycles
- `activate_document_management_tools`: create_document, get_document, update_document, update_project

**GitHub** (usar `activate_*_tools`):
- `activate_file_management_tools`: get_file_contents, delete_file
- `activate_repository_information_tools`: get_commit, get_release, get_tag, get_issue, get_me
- `activate_release_and_tag_management_tools`: list_releases, get_release_by_tag, list_tags
- `activate_search_and_discovery_tools`: search_code, search_repositories, search_users
- `activate_branch_and_commit_tools`: list_branches, get_branch_commits

**Ejemplo de activación**:
```python
# ❌ Incorrecto (falla)
mcp_linear_create_issue(...)

# ✅ Correcto
activate_issue_management_tools()
mcp_linear_create_issue(...)
```

**Referencia completa**: Skill global `linear-mcp-tool` para troubleshooting.

---

## 🔄 Workflows Especiales

### Schemas DB del Ecosistema (OPA-343)

**Nota**: Este repo (Python streaming) no crea SQLAlchemy models directamente, pero para contexto:

El ecosistema usa [state-db-schemas.yaml.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/infrastructure/state-db-schemas.yaml.md) como **source of truth** de schemas DB reales.

**Tablas del módulo Quotes**:
- `quotes.quotes` - Almacenado en opa-quotes-storage (TimescaleDB)
- Este streamer escribe via HTTP a opa-quotes-storage (no conexión PostgreSQL directa)

---

## ⚠️ Errores Críticos a Evitar

### 1. Puerto 5432 en Windows

```
❌ Conectar a localhost:5432 para PostgreSQL Docker
✅ Usar puerto 5433+ (ver service-inventory.md en supervisor)
```

**Causa**: PostgreSQL local Windows ocupa 5432.

### 2. Commits sin referencia a issue

```
❌ git commit -m "Fix bug"
✅ git commit -m "OPA-XXX: Fix bug description"
```

**Convención**: TODOS los commits referencian issue Linear.

### 3. Actualizar descripción en lugar de comentar

```
❌ mcp_linear_update_issue(body="[REACTIVADA] ...")
✅ mcp_linear_create_comment(body="## Reactivada...") + update_issue(state="In Progress")
```

**Regla**: Progreso va en COMENTARIOS, no en descripción.

---

## 🔧 Convenciones Rápidas

### Código y Commits

| Elemento | Convención |
|----------|------------|
| **Idioma código** | Inglés (clases, funciones, variables) |
| **Idioma interacción** | Español (comentarios Linear, PRs, docs) |
| **Formato commit** | `OPA-XXX: Descripción imperativa` |
| **Branches** | `username/opa-xxx-descripcion` |

### Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Lenguaje principal | Python 3.12 (NO 3.13) |
| Async runtime | asyncio |
| Data source | yfinance (Fase 1-2) |
| HTTP client | httpx, aiohttp |
| Validation | Pydantic 2.5+ |
| Cache | Redis 7+ |
| Monitoring | Prometheus |

---

*Documento actualizado por OPA-378 - Corrección stack Rust → Python (ADR-019).*
