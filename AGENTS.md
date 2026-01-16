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

## 📚 Agent Skills (CONSULTAR PRIMERO)

Este repositorio incluye skills especializados para guiar el trabajo:

| Skill | Propósito | Cuándo consultar |
|-------|-----------|------------------|
| **[git-linear-workflow](.github/skills/git-linear-workflow/SKILL.md)** | Workflow Git+Linear completo | Al trabajar en issues (branch, commit, merge, cierre) |
| **[linear-mcp-tool](.github/skills/linear-mcp-tool/SKILL.md)** | Errores comunes Linear MCP | Al usar mcp_linear tools (errores, fixes) |
| **[run-efficiency](.github/skills/run-efficiency/SKILL.md)** | Gestión tokens, pre-Done checklist | En tareas complejas, antes de marcar Done |

**Guías de referencia** (supervisor):
- **[code-conventions.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/guides/code-conventions.md)**: Estándares código, testing, CI/CD
- **[technology-stack.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/guides/technology-stack.md)**: Stack tecnológico consolidado

**Convención idiomática**:
- **Código y nombres técnicos** (clases, funciones, commits): **Inglés**
- **Interacción con usuarios** (comentarios Linear, PRs, docs narrativa): **Español**

> **Sincronizado desde**: OPA_Machine supervisor (OPA-264)

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

**Ejemplo**:
```markdown
# Detectar fallo
Tool mcp_linear_create_comment failed: currently disabled

# 1. Activar grupo
activate_issue_management_tools()

# 2. Reintentar operación EXACTA
mcp_linear_create_comment(issueId="OPA-XXX", body="...")
```

### Tools que Requieren Activación

| Grupo | Tool de Activación | Cuándo Usar |
|-------|-------------------|-------------|
| Linear Issues | `activate_issue_management_tools()` | Crear/actualizar issues, labels |
| Linear Docs | `activate_document_management_tools()` | Crear/actualizar documentos |
| GitHub PRs | `activate_pull_request_review_tools()` | Crear/revisar PRs |
| GitHub Repos | `activate_repository_management_tools()` | Crear repos, branches |

**Ver**: `OPA_Machine/AGENTS.md` sección "Gestión de Tools MCP" para tabla completa.

---

## 🛡️ Validación de Convenciones

**REGLA CRÍTICA**: Antes de ejecutar acciones que modifican estado, validar convenciones.

### Convenciones Obligatorias

1. **Commits**: DEBEN incluir referencia a issue (`OPA-XXX`)
2. **Issues**: DEBEN crearse en Linear ANTES de implementar
3. **Branches**: DEBEN seguir patrón `username/opa-xxx-descripcion`
4. **Tests**: DEBEN ejecutarse antes de marcar Done

### 📝 Regla Crítica: Comentarios vs Descripción en Issues

**PRINCIPIO**: La **descripción** de una issue es la **especificación inicial**. Los **comentarios** son el **registro de progreso**.

**Comportamiento requerido**:

| Acción | Tool Correcta | Tool Incorrecta |
|--------|---------------|-----------------|
| Reportar avance parcial | `mcp_linear_create_comment()` | ❌ `mcp_linear_update_issue(body=...)` |
| Reactivar issue cerrada | `mcp_linear_create_comment()` + `update_issue(state="In Progress")` | ❌ Solo modificar descripción |
| Documentar error encontrado | `mcp_linear_create_comment()` | ❌ Editar descripción |
| Añadir diagnóstico | `mcp_linear_create_comment()` | ❌ Modificar descripción |
| Cerrar con resumen | `mcp_linear_create_comment()` + `update_issue(state="Done")` | ❌ Solo cambiar estado |

**¿Por qué?**:
- **Trazabilidad**: Comentarios tienen timestamps automáticos → historial auditable
- **Notificaciones**: Comentarios notifican a watchers → mejor colaboración
- **Reversibilidad**: Descripción original preservada → contexto no se pierde
- **Multi-agente**: Varios agentes pueden comentar sin conflictos de edición

**¿Cuándo SÍ modificar descripción?**:
- ✅ Corregir typos en la especificación original
- ✅ Añadir criterios de aceptación faltantes (antes de empezar trabajo)
- ✅ Actualizar estimación inicial
- ❌ NUNCA para reportar progreso, errores o reactivaciones

### Checkpoint Pre-Acción

Si detectas violación, **DETENER** y devolver control al usuario:

```markdown
⚠️ **Acción Bloqueada - Violación de Convención**

**Acción planeada**: `git commit -m "Fix bug"`
**Violación**: Commit sin referencia a issue (OPA-XXX)

**Opciones**:
1. Crear issue en Linear primero → Usar OPA-XXX en commit
2. Si issue existe → Añadir referencia al mensaje

¿Cómo deseas proceder?
```

**El agente debe esperar respuesta del usuario antes de continuar.**

---

## ⚠️ Validación Pre-cierre de Issue (CRÍTICO)

**REGLA DE ORO**: Si un archivo NO está en GitHub en rama `main`, la issue NO está "Done".

### Checklist OBLIGATORIO antes de mover issue a "Done"

```bash
# 0. LEER COMENTARIOS DE LA ISSUE (PRIMERO)
# - Revisar TODOS los comentarios (especialmente los más recientes)
# - Verificar que no hay instrucciones contradictorias

# 1. Verificar estado de git
git status  # Debe estar limpio

# 2. Confirmar que archivos mencionados en la issue EXISTEN
ls ruta/al/archivo-nuevo.md

# 3. Commitear con mensaje correcto
git add [archivos]
git commit -m "OPA-XXX: Descripción clara"

# 4. Pushear a GitHub
git push origin main
# O si trabajas en rama:
git push origin <nombre-rama>

# 5. VERIFICAR en GitHub web que commit aparece

# 6. Si trabajaste en rama feature: MERGEAR a main
git checkout main
git pull origin main
git merge --squash <nombre-rama>
git commit -m "OPA-XXX: Descripción completa"
git push origin main

# 7. Eliminar branch (local + remota)
git branch -d <nombre-rama>
git push origin --delete <nombre-rama> 2>/dev/null || true

# 8. Solo ENTONCES: Mover issue a "Done" en Linear
```

### Template de Comentario Final

TODO cierre de issue DEBE incluir comentario con este formato:

```markdown
## ✅ Resolución

🤖 **Agente opa-quotes-streamer**

**Pre-checks**:
- [x] Leídos TODOS los comentarios de la issue
- [x] Verificadas dependencias mencionadas (si hay)

**Cambios realizados**:
- [x] Archivo X creado/modificado
- [x] Archivo Y actualizado

**Commits**:
- Hash: abc1234
- Mensaje: "OPA-XXX: Descripción"
- Link: https://github.com/Ocaxtar/opa-quotes-streamer/commit/abc1234

**Verificación**:
- [x] Archivos confirmados en `git status`
- [x] Commit pusheado a GitHub
- [x] Rama mergeada a `main`
- [x] Archivos visibles en GitHub web en rama `main`

**Tests** (si aplica):
- [x] pytest pasado (X/Y tests)
- [x] Linter sin errores

Issue cerrada.
```

### Errores Comunes que Causan Pérdida de Trabajo

| Error | Consecuencia | Solución |
|-------|--------------|----------|
| ❌ Cerrar issue sin verificar archivos en `main` | Trabajo perdido en rama sin mergear | Siempre verificar en GitHub web |
| ❌ Pushear a rama pero NO mergear a main | Código no desplegable | Siempre mergear rama a `main` |
| ❌ Commitear pero NO pushear | Archivos solo en local | `git push` SIEMPRE antes de cerrar |
| ❌ Asumir que archivos están commiteados | Archivos solo en working directory | `git status` debe estar limpio |
| ❌ Cerrar issue sin comentario final | Sin trazabilidad | Template SIEMPRE |

### Prefijo Obligatorio en Comentarios

**TODO comentario en Linear DEBE tener prefijo**:

```
🤖 Agente opa-quotes-streamer: [tu mensaje]
```

**Violaciones detectadas por auditoría supervisor**:
- Issue sin comentario → REABIERTA
- Comentario sin prefijo → Backfill correctivo

---

**Última sincronización con supervisor**: 2026-01-16
**Versión normativa**: 2.0.0 (Agent Skills)
