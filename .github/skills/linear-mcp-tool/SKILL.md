---
name: linear-mcp-tool
description: Errores comunes y soluciones al usar Linear MCP tools. Cubre activación de tools, UUIDs de teams/labels, formato correcto de parámetros, y patrones de uso seguro.
version: 1.0.0
author: OPA Team
tags: [linear, mcp, troubleshooting, tools, gotchas]
---

# Linear MCP Tool Skill

Guía rápida para resolver errores comunes al usar el MCP de Linear.

## Cuándo usar este skill

- **Error con tool Linear** (disabled, not found, validation error)
- **Crear issue/label** por primera vez en sesión
- **Aplicar labels de grupo** (`repo →`)
- **Reactivar issue cerrada** correctamente

---

## 🚨 Error 1: "teamId must be a UUID"

### Solución

```python
# ✅ CORRECTO: Nombre exacto del team
mcp_linear_create_issue(
    team="OPA_Machine",
    title="..."
)
```

**UUID del team OPA**: `1323a5e3-29fe-448c-a601-bc6b65d51d4e`

---

## 🚨 Error 2: Labels de grupo sin prefijo

```python
# ✅ CORRECTO: Sin prefijo "repo →"
mcp_linear_update_issue(
    id="OPA-XXX",
    labels=["Feature", "opa-quotes-api"]  # NO "repo → opa-quotes-api"
)
```

---

## 🚨 Error 3: Tool disabled

### Tabla de Activación

| Categoría | Tool para activar |
|-----------|------------------|
| **Issues/Labels** | `activate_issue_management_tools()` |
| **Tracking** | `activate_issue_tracking_tools()` |
| **Workspace** | `activate_workspace_overview_tools()` |
| **Teams/Users** | `activate_team_and_user_management_tools()` |

### Tools Siempre Disponibles (sin activación)

- `mcp_linear_create_issue`
- `mcp_linear_update_issue`
- `mcp_linear_create_comment`
- `mcp_linear_list_issues`
- `mcp_linear_list_issue_labels`

---

## 📝 Patrón: Comentarios vs Descripción

| Acción | Tool Correcta |
|--------|---------------|
| Reportar progreso | `mcp_linear_create_comment()` |
| Reactivar issue | `create_comment()` + `update_issue(state=...)` |
| Cerrar con resumen | `create_comment()` + `update_issue(state="Done")` |

**NUNCA** modificar descripción para reportar progreso.

---

## 📋 Ejemplo: Cerrar Issue

```python
mcp_linear_create_comment(
    issueId="OPA-XXX",
    body="## ✅ Issue Completada\n\n**Cambios**: ...\n**Tests**: XX passed"
)

mcp_linear_update_issue(id="OPA-XXX", state="Done")
```

---

## 🔗 Integración con Otros Skills

| Skill | Integración |
|-------|-------------|
| **git-linear-workflow** | Workflow completo usando estos tools |
| **run-efficiency** | Pre-Done checklist incluye comentario final |

---

> **Sincronizado desde**: OPA_Machine supervisor (OPA-263)
