---
name: run-efficiency
description: Gestión eficiente de tokens, detección de context bloat, planificación multi-run y validación pre-Done. Previene runs truncadas o incompletas.
version: 1.0.0
author: OPA Team
tags: [efficiency, tokens, context, planning, validation]
---

# Run Efficiency Skill

Normativas para maximizar eficiencia de tokens, prevenir trabajo incompleto, y mantener visibilidad de progreso.

## Cuándo activar este skill

- **Siempre** al inicio de tareas >3 pasos
- **Siempre** antes de marcar cualquier issue como Done
- Cuando usuario reporte trabajo incompleto o truncado

---

## Regla 1: manage_todo_list Obligatoria

### Cuándo usar
- **SIEMPRE** en tareas >3 pasos
- **SIEMPRE** cuando tarea involucre múltiples archivos

### Reglas estrictas
- ❌ **NUNCA** tener >1 tarea "in-progress" simultáneamente
- ❌ **NUNCA** marcar "completed" sin haber ejecutado la acción
- ✅ **SIEMPRE** actualizar inmediatamente tras completar
- ✅ **OBLIGATORIO**: Último paso = "Generar reporte Context Bloat"

---

## Regla 2: Context Bloat Detection

### Cuándo ejecutar
- **Evaluación al inicio**: Detectar contexto innecesario
- **Reporte al final**: SIEMPRE generar mini-reporte

### Reporte final (OBLIGATORIO)

```markdown
📊 **Context usado esta run**:
- Archivos leídos: X (relevantes: Y)
- Herramientas llamadas: Z
- Contexto no usado: [lista si aplica]
```

---

## Regla 3: Plan Multi-Run

### Cuándo aplicar
- Tarea requiere >5 llamadas a herramientas
- Tarea afecta múltiples repos/archivos

### Workflow

1. Proponer plan con estimación de runs
2. Guardar plan en descripción de issue
3. Añadir comentario al completar cada run

---

## Regla 4: Pre-Done Checklist

**NUNCA** marcar issue Done sin validar:

```markdown
⏸️ **Pre-Done Validation - OPA-XXX**

- [ ] Código implementado
- [ ] Tests ejecutados y pasando
- [ ] Documentación actualizada
- [ ] manage_todo_list vacía
- [ ] Convenciones cumplidas (commits con OPA-XXX)

**Estado**: X/5 ✅
```

---

## Señales de Alerta

Si observas estos síntomas, **DETENER y avisar**:
- Tendencia a "resumir" en lugar de ejecutar
- Impulso de cerrar rápido sin validar

---

## Anti-Patrones a Evitar

| ❌ Anti-Patrón | ✅ Correcto |
|----------------|-------------|
| Marcar Done sin tests | Ejecutar tests primero |
| "Continúo después" sin trackear | manage_todo_list + comentario |
| Plan mental sin documentar | Plan escrito en issue |
| Cerrar solo cambiando estado | Comentario + estado |

---

## 🔗 Integración con Otros Skills

| Skill | Integración |
|-------|-------------|
| **git-linear-workflow** | Pre-Done checklist antes de cerrar |
| **linear-mcp-tool** | Comentario final obligatorio |

---

> **Sincronizado desde**: OPA_Machine supervisor (OPA-263)
