#!/usr/bin/env bash
# check_sync.sh - Verifica sincronización Git y aplica pull automático seguro
# Parte del skill workspace-sync (OPA_Machine)

set -euo pipefail

# Colores
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

BRANCH="${1:-main}"

echo "🔄 Verificando sincronización con origin/$BRANCH..."

# 1. Fetch remoto
if ! git fetch origin --quiet 2>/dev/null; then
    echo -e "${YELLOW}⚠️  No se pudo conectar con el remoto${NC}"
    exit 5
fi

# 2. Detectar divergencias
LOCAL_AHEAD=$(git rev-list origin/"$BRANCH".."$BRANCH" --count 2>/dev/null || echo "0")
REMOTE_AHEAD=$(git rev-list "$BRANCH"..origin/"$BRANCH" --count 2>/dev/null || echo "0")

# 3. Casos según estado
if [[ "$LOCAL_AHEAD" -eq 0 && "$REMOTE_AHEAD" -eq 0 ]]; then
    echo -e "${GREEN}✅ Sincronizado con origin/$BRANCH${NC}"
    exit 0
fi

if [[ "$LOCAL_AHEAD" -gt 0 && "$REMOTE_AHEAD" -eq 0 ]]; then
    echo -e "${YELLOW}⚠️  Tienes $LOCAL_AHEAD commit(s) local(es) sin push${NC}"
    exit 2
fi

if [[ "$LOCAL_AHEAD" -gt 0 && "$REMOTE_AHEAD" -gt 0 ]]; then
    echo -e "${RED}❌ Divergencia detectada: $LOCAL_AHEAD local, $REMOTE_AHEAD remoto${NC}"
    echo "   Requerida resolución manual: git pull --rebase o git merge"
    exit 4
fi

# 4. Cambios remotos disponibles → Verificar si son solo docs
if [[ "$REMOTE_AHEAD" -gt 0 ]]; then
    echo "📥 Detectados $REMOTE_AHEAD commit(s) remotos nuevos"
    
    # Verificar archivos sin commitear
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo -e "${YELLOW}⚠️  Tienes cambios sin commitear. Pull manual requerido.${NC}"
        exit 3
    fi
    
    # Obtener archivos modificados en commits remotos
    CHANGED_FILES=$(git diff --name-only "$BRANCH" "origin/$BRANCH" 2>/dev/null || echo "")
    
    # Verificar si TODOS los archivos están en whitelist de docs
    DOCS_ONLY=true
    while IFS= read -r file; do
        if [[ ! "$file" =~ ^(docs/|AGENTS\.md|\.github/skills/|README\.md|ROADMAP\.md) ]]; then
            DOCS_ONLY=false
            break
        fi
    done <<< "$CHANGED_FILES"
    
    if [[ "$DOCS_ONLY" == "true" ]]; then
        echo -e "${GREEN}🔄 Solo cambios en documentación. Aplicando pull automático...${NC}"
        git pull origin "$BRANCH" --quiet
        echo -e "${GREEN}✅ Pull automático completado${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  Cambios remotos incluyen código. Pull manual requerido.${NC}"
        echo "   Archivos modificados:"
        echo "$CHANGED_FILES" | sed 's/^/     - /'
        exit 3
    fi
fi

# Fallback
exit 0
