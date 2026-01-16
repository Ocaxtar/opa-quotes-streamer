---
name: git-linear-workflow
description: Workflow completo Git+Linear para desarrollo en ecosistema OPA. Cubre gestión de ramas, commits, PRs, integración con issues Linear, activación de MCPs, y validación pre-Done. Workflow 1 Issue = 1 Branch = 1 Merge a main.
version: 1.0.0
author: OPA Team
tags: [git, linear, workflow, mcp, branches, issues]
---

# Git + Linear Workflow Skill

Workflow completo para integración Git (código) ↔ Linear (planificación) con convenciones estrictas de branches, commits y cierre de issues.

## Cuándo usar este skill

- **Iniciar trabajo** en nueva issue (crear branch, mover a In Progress)
- **Commitear cambios** con referencia a issue
- **Mergear a main** antes de cerrar issue
- **Activar MCPs** de Linear/GitHub correctamente
- **Validar pre-Done** con checklist obligatoria

## Principios Fundamentales

**Fuente de verdad**: Linear (planificación) + GitHub (código)

**Regla de oro**: 1 Issue = 1 Branch = 1 Squash Commit en main

**Objetivo**: Minimizar fricción entre gestión de código y gestión de trabajo.

---

## 🔧 Gestión de Tools Linear MCP

**CRÍTICO**: Muchas tools de Linear requieren activación explícita antes de uso.

### Tools que Requieren Activación

| Grupo | Tool de Activación | Cuándo usar |
|-------|-------------------|-------------|
| **Issues/Labels** | `activate_issue_management_tools()` | Crear/actualizar issues, labels |
| **Tracking** | `activate_issue_tracking_tools()` | Obtener status, attachments |
| **Workspace** | `activate_workspace_overview_tools()` | Listar proyectos, labels, teams |
| **Teams/Users** | `activate_team_and_user_management_tools()` | Info de teams, users |

### Manejo de Errores

Si una tool falla con `currently disabled by the user`:

```python
# ❌ INCORRECTO: Continuar sin la tool
"No pude crear issue, continuando..."

# ✅ CORRECTO: Activar y reintentar
activate_issue_management_tools()
mcp_linear_create_issue(...)  # Reintentar MISMA operación
```

**Regla**: NUNCA saltar un paso porque una tool falló. Siempre activar y reintentar.

---

## 📝 Comentarios vs Descripción en Issues

**PRINCIPIO**: La **descripción** es la especificación inicial. Los **comentarios** son el registro de progreso.

| Acción | Tool Correcta | Tool Incorrecta |
|--------|---------------|------------------|
| Reportar progreso | `mcp_linear_create_comment()` | ❌ `update_issue(body=...)` |
| Reactivar issue | `create_comment()` + `update_issue(state=...)` | ❌ Solo modificar descripción |
| Cerrar con resumen | `create_comment()` + `update_issue(state="Done")` | ❌ Solo cambiar estado |

---

## 🌿 Gestión de Ramas

### Convenciones de Ramas

**Rama principal**: `main` - Siempre desplegable, historia limpia

**Ramas de desarrollo**:
- **Formato**: `{username}/OPA-{issue-id}-{descripcion-corta}`
- **Ejemplos**: `oscarcalvo/OPA-261-migrate-guides-to-skills`
- **Eliminar tras merge**: OBLIGATORIO

---

## 📝 Workflow Completo (Issue → Done)

### Fase 1: Iniciar Issue

```bash
# 1. Mover issue a "In Progress" en Linear
mcp_linear_update_issue(id="OPA-XXX", state="In Progress")

# 2. Crear branch desde main actualizado
git checkout main && git pull origin main
git checkout -b {username}/OPA-{issue-id}-{descripcion-corta}
```

### Fase 2: Desarrollo

```bash
git add <archivos>
git commit -m "WIP OPA-XXX: descripción progreso"
git push origin {branch}
```

### Fase 3: Completar Issue

```bash
# Mergear a main (squash)
git checkout main && git pull origin main
git merge --squash {branch}
git commit -m "OPA-XXX: Descripción completa"
git push origin main

# Eliminar branch
git branch -d {branch}
git push origin --delete {branch}
```

### Fase 4: Cierre en Linear

```python
mcp_linear_create_comment(issueId="OPA-XXX", body="## ✅ Issue Completada\n...")
mcp_linear_update_issue(id="OPA-XXX", state="Done")
```

---

## ⚠️ Validación Pre-Cierre (Checklist Obligatoria)

```markdown
⏸️ **Pre-Done Validation - OPA-XXX**

- [ ] Código implementado
- [ ] Tests ejecutados y pasando
- [ ] Documentación actualizada
- [ ] manage_todo_list vacía
- [ ] Commits con OPA-XXX
- [ ] **Rama mergeada a main** ← CRÍTICO
- [ ] Comentario final añadido

**Estado**: X/7 ✅
```

---

## 🔗 Integración con Otros Skills

| Skill | Integración |
|-------|-------------|
| **run-efficiency** | Pre-Done checklist obligatoria antes de cerrar |
| **linear-mcp-tool** | Errores comunes MCPs |

---

> **Sincronizado desde**: OPA_Machine supervisor (OPA-263)
