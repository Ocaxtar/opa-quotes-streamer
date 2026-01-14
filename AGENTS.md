# AGENTS.md - Guía para Agentes de IA

> 🎯 **Guía operativa para el repositorio opa-quotes-streamer**  
> Consultar guías del supervisor para contexto global del ecosistema

## Información del Repositorio

**Nombre**: opa-quotes-streamer  
**Módulo**: Cotización (Módulo 5)  
**Rol**: Streaming de cotizaciones en tiempo real  
**Equipo Linear**: OPA  
**Label Linear**: `opa-quotes-streamer`  
**Supervisor**: [OPA_Machine](https://github.com/Ocaxtar/OPA_Machine)

## 📚 Guías Especializadas (CONSULTAR PRIMERO)

**Importante**: Antes de trabajar en este repositorio, consulta las guías centralizadas del supervisor.

| Guía | Propósito | Cuándo consultar |
|------|-----------|------------------|
| **[workflow-git-linear.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/guides/workflow-git-linear.md)** | Workflow Git+Linear completo | Al trabajar en issues (branch, commit, merge, cierre) |
| **[multi-workspace-guide.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/guides/multi-workspace-guide.md)** | Arquitectura 20 repos, coordinación | Al crear issues cross-repo, entender labels Linear |
| **[code-conventions.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/guides/code-conventions.md)** | Estándares código, testing, CI/CD | Al escribir código, configurar tests, Docker |
| **[technology-stack.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/guides/technology-stack.md)** | Stack tecnológico consolidado | Al elegir librerías, evaluar rendimiento |
| **[linear-mcp-quickstart.md](https://github.com/Ocaxtar/OPA_Machine/blob/main/docs/guides/linear-mcp-quickstart.md)** | Errores comunes Linear MCP | Al usar mcp_linear tools (errores, fixes) |

**Convención idiomática**:
- **Código y nombres técnicos** (clases, funciones, commits): **Inglés**
- **Interacción con usuarios** (comentarios Linear, PRs, docs narrativa): **Español**

## Contexto del Servicio

Este servicio es responsable de:
1. **Conexión a APIs de mercado** (Yahoo Finance, Alpha Vantage)
2. **Streaming de cotizaciones** en tiempo real
3. **Publicación de eventos** para consumo por otros servicios
4. **Gestión de reconexión** y circuit breaker

### Posición en el Ecosistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPA_Machine (Supervisor)                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ quotes-api   │  │ quotes-      │  │ quotes-      │
│              │◄─┤ streamer ◄───┤──┤ storage      │
│              │  │ (ESTE REPO)  │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Dependencias

| Servicio | Tipo | Propósito |
|----------|------|-----------|
| `opa-quotes-storage` | Downstream | Persistencia de cotizaciones |
| `opa-quotes-api` | Downstream | Consulta de cotizaciones históricas |
| Redis | Infraestructura | Pub/Sub para eventos |

## Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| Lenguaje | Rust | 1.75+ |
| Runtime async | Tokio | Latest |
| HTTP Client | reqwest | Latest |
| Serialización | serde | Latest |
| WebSocket | tokio-tungstenite | Latest |

## Estructura del Proyecto

```
opa-quotes-streamer/
├── src/
│   ├── main.rs           # Entry point
│   ├── config/           # Configuración
│   ├── connectors/       # Conectores a APIs externas
│   ├── events/           # Definición de eventos
│   └── streaming/        # Lógica de streaming
├── tests/
│   ├── integration/      # Tests de integración
│   └── unit/             # Tests unitarios
├── Cargo.toml
├── Dockerfile
└── docker-compose.yml
```

## Convenciones de Desarrollo

### Commits

Formato: `<tipo>(<scope>): <descripción> (OPA-XXX)`

Tipos permitidos:
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Documentación
- `refactor`: Refactorización
- `test`: Tests
- `chore`: Mantenimiento

Ejemplo: `feat(connectors): Add Alpha Vantage connector (OPA-123)`

### Branches

Patrón: `username/opa-xxx-descripcion`

Ejemplo: `ocaxtar/opa-123-alpha-vantage-connector`

### Testing

```bash
# Tests unitarios
cargo test

# Tests de integración
cargo test --test integration

# Con coverage
cargo tarpaulin --out Html
```

## Contratos

### Eventos Publicados

| Evento | Canal Redis | Schema |
|--------|-------------|--------|
| `QuoteReceived` | `quotes:realtime` | Ver `docs/contracts/events/quote-received.md` |
| `StreamError` | `quotes:errors` | Ver `docs/contracts/events/stream-error.md` |

### APIs Consumidas

| API | Propósito | Documentación |
|-----|-----------|---------------|
| Yahoo Finance | Cotizaciones realtime | [yfinance docs](https://pypi.org/project/yfinance/) |
| Alpha Vantage | Cotizaciones premium | [alphavantage.co](https://www.alphavantage.co/documentation/) |

## Comandos Útiles

```bash
# Desarrollo
cargo build
cargo run

# Producción
cargo build --release

# Docker
docker-compose up -d

# Logs
docker-compose logs -f streamer
```

## 🔧 Gestión de Tools MCP

### Tools que Requieren Activación

| Grupo | Tool de Activación | Cuándo Usar |
|-------|-------------------|-------------|
| **Issues Linear** | `activate_issue_management_tools()` | Crear/actualizar issues |
| **Repos GitHub** | `activate_repository_management_tools()` | Branches, PRs |
| **Search** | `activate_search_and_discovery_tools()` | Buscar código |

### Patrón de Uso

```markdown
# Si tool falla con "disabled":
1. Activar grupo correspondiente
2. Reintentar operación
3. NUNCA saltar el paso
```

## 🛡️ Pre-Issue Close Checklist

Antes de marcar una issue como Done:

- [ ] Tests ejecutados y pasando (`cargo test`)
- [ ] Código formateado (`cargo fmt`)
- [ ] Linting sin errores (`cargo clippy`)
- [ ] Documentación actualizada si aplica
- [ ] PR mergeado a main

## 📝 Comentarios vs Descripción en Issues

**PRINCIPIO**: La **descripción** de una issue es la **especificación inicial**. Los **comentarios** son el **registro de progreso**.

| Acción | Tool Correcta | Tool Incorrecta |
|--------|---------------|-----------------|
| Reportar avance parcial | `mcp_linear_create_comment()` | ❌ `mcp_linear_update_issue(body=...)` |
| Reactivar issue cerrada | `mcp_linear_create_comment()` + `update_issue(state="In Progress")` | ❌ Solo modificar descripción |
| Documentar error encontrado | `mcp_linear_create_comment()` | ❌ Editar descripción |
| Añadir diagnóstico | `mcp_linear_create_comment()` | ❌ Modificar descripción |
| Cerrar con resumen | `mcp_linear_create_comment()` + `update_issue(state="Done")` | ❌ Solo cambiar estado |

**Rationale**:
- **Trazabilidad**: Comentarios tienen timestamps automáticos → historial auditable
- **Notificaciones**: Comentarios notifican a watchers → mejor colaboración
- **Reversibilidad**: Descripción original preservada → contexto no se pierde
- **Multi-agente**: Varios agentes pueden comentar sin conflictos de edición

**¿Cuándo SÍ modificar descripción?**:
- ✅ Corregir typos en la especificación original
- ✅ Añadir criterios de aceptación faltantes (antes de empezar trabajo)
- ❌ NUNCA para reportar progreso, errores o reactivaciones

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

## Contacto y Escalación

**Para decisiones de arquitectura**: Crear issue con label `architecture` en supervisor  
**Para bugs críticos**: Usar label `urgent` + `P0` en Linear  
**Supervisor**: [OPA_Machine](https://github.com/Ocaxtar/OPA_Machine)

---

📝 **Este documento debe mantenerse sincronizado con el supervisor**

**Última sincronización con supervisor**: 2026-01-14
