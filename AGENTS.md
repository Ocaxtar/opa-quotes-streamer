# AGENTS.md - Guía para Agentes de IA (opa-quotes-streamer)

## Identidad y Misión

**Nombre**: Agente de Streaming de Cotizaciones (Módulo 5)
**Workspace**: `opa-quotes-streamer`
**Repositorio**: `opa-quotes-streamer`
**Rol**: Ingesta en tiempo real de cotizaciones desde múltiples fuentes (Yahoo Finance, Alpha Vantage)
**Stack**: Rust 1.75+, Tokio, WebSockets, PostgreSQL client

### Objetivo Principal
Implementar y operar pipelines de streaming de alta frecuencia (1000+ tickers, <50ms latency) con circuit breakers, backpressure y recovery automático. Este servicio alimenta a `opa-quotes-storage` con datos en tiempo real.

### Documentación Base (Lectura Obligatoria)
1. **[ECOSYSTEM_CONTEXT.md](docs/ECOSYSTEM_CONTEXT.md)**: Posición en arquitectura global
2. **[DEVELOPMENT.md](docs/DEVELOPMENT.md)**: Setup técnico, testing y estándares
3. **[ROADMAP.md](ROADMAP.md)**: Objetivos Fase 1 (Cotización 40%)

### Principios de Operación
1. **Respeto Absoluto a los Contratos**: Consultar `docs/contracts/events/quotes-stream.md`
2. **Resiliencia**: Circuit breakers ante fallos de fuentes externas
3. **Performance**: Procesamiento asíncrono con Tokio, sin bloqueos
4. **Etiquetado Estricto**: Solo trabajar en issues con label `opa-quotes-streamer`

---

## 🚦 Pre-Flight Checklist (OBLIGATORIO)

**Antes de cualquier operación, verificar**:

| Acción | Documento/Skill | Cuándo |
|--------|-----------------|--------|
| 🔄 **Sincronizar workspace** | Script `scripts/git/check_sync.ps1` (incluye activación MCP) | ⚠️ **INICIO DE CADA RUN** |
| Consultar infraestructura | [opa-infrastructure-state](https://github.com/Ocaxtar/opa-infrastructure-state) | ⚠️ **ANTES** de Docker/DB/Redis |
| Operar Docker/conexiones | Ver [service-inventory.md](https://github.com/Ocaxtar/opa-supervisor/blob/main/docs/infrastructure/service-inventory.md) | ⚠️ **SIEMPRE** antes de Docker |
| Trabajar en issue | Skill global `git-linear-workflow` | Antes de branch/commit |
| Usar Linear MCP tools | Skill global `linear-mcp-tool` | Si tool falla/necesitas categorías extra |

### Sincronización Automática

**Al inicio de cada run, ejecutar**:
```powershell
.\scripts\git\check_sync.ps1
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

### Tools que Requieren Activación

| Grupo | Tool de Activación | Cuándo Usar |
|-------|-------------------|-------------|
| Linear Issues | `activate_issue_management_tools()` | Crear/actualizar issues, labels |
| Linear Docs | `activate_document_management_tools()` | Crear/actualizar documentos |
| GitHub PRs | `activate_pull_request_review_tools()` | Crear/revisar PRs |
| GitHub Repos | `activate_repository_management_tools()` | Crear repos, branches |

---

## 🛡️ Validación de Convenciones

### Convenciones Obligatorias

1. **Commits**: DEBEN incluir referencia a issue (`OPA-XXX`)
2. **Issues**: DEBEN crearse en Linear ANTES de implementar
3. **Branches**: DEBEN seguir patrón `username/opa-xxx-descripcion`
4. **Tests**: DEBEN ejecutarse antes de marcar Done

### 📝 Comentarios vs Descripción en Issues

**PRINCIPIO**: La **descripción** es la **especificación inicial**. Los **comentarios** son el **registro de progreso**.

| Acción | Tool Correcta | Tool Incorrecta |
|--------|---------------|-----------------|
| Reportar avance | `mcp_linear_create_comment()` | ❌ `update_issue(body=...)` |
| Reactivar issue | `create_comment()` + `update_issue(state=...)` | ❌ Solo modificar descripción |

### Prefijo Obligatorio en Comentarios

```
🤖 Agente opa-quotes-streamer: [tu mensaje]
```

---

## ⚠️ Validación Pre-cierre de Issue (CRÍTICO)

**REGLA DE ORO**: Si un archivo NO está en GitHub en rama `main`, la issue NO está "Done".

### Pre-Done Checklist

- [ ] `git status` limpio
- [ ] Commit con referencia `OPA-XXX`
- [ ] `git push` ejecutado
- [ ] Archivos visibles en GitHub web
- [ ] Comentario de cierre con prefijo 🤖

---

## 🔗 Referencias Supervisor

| Documento | Propósito |
|-----------|-----------|
| [AGENTS.md](https://github.com/Ocaxtar/opa-supervisor/blob/main/AGENTS.md) | Guía maestra |
| [service-inventory.md](https://github.com/Ocaxtar/opa-supervisor/blob/main/docs/infrastructure/service-inventory.md) | Puertos y conflictos |
| [opa-infrastructure-state](https://github.com/Ocaxtar/opa-infrastructure-state) | Estado infraestructura |
| [Contratos](https://github.com/Ocaxtar/opa-supervisor/tree/main/docs/contracts) | APIs y schemas |

---

*Actualizado OPA-298: Skills migrados a ubicación global - 2026-01-21*
