# scripts/git/check_sync.ps1
# Verifica sincronización Git y aplica pull automático de documentación si es seguro

$ErrorActionPreference = "Stop"

function Safe-GitCount([string]$range) {
    try {
        $count = git rev-list $range --count 2>$null
        if ([string]::IsNullOrWhiteSpace($count)) { return 0 }
        return [int]$count
    } catch {
        return 0
    }
}

# Repo + branch
$repoRoot = git rev-parse --show-toplevel
$repoName = Split-Path -Path $repoRoot -Leaf
$branch = git rev-parse --abbrev-ref HEAD

# 1. Fetch sin descargar
Write-Output "🔍 Verificando estado remoto..."
try {
    git fetch origin --quiet 2>$null
} catch {
    Write-Output "⚠️ No se pudo conectar con remoto"
    exit 5
}

# 2. Detectar divergencias
$localAhead = Safe-GitCount("origin/$branch..$branch")
$remoteAhead = Safe-GitCount("$branch..origin/$branch")

# 3. Verificar archivos sin commit
$uncommitted = @(git status --porcelain)
if ($uncommitted.Count -gt 0) {
    Write-Output "⚠️ Archivos sin commit detectados:"
    git status --short
    Write-Output ""
    Write-Output "Commitea o stashea antes de sincronizar"
    exit 1
}

# 4. Tomar decisión
if ($localAhead -eq 0 -and $remoteAhead -eq 0) {
    Write-Output "✅ Workspace sincronizado"
    exit 0
}
elseif ($localAhead -gt 0 -and $remoteAhead -eq 0) {
    Write-Output "⚠️ $localAhead commits locales sin push:"
    git log --oneline "origin/$branch..$branch"
    Write-Output ""
    Write-Output "Acción recomendada: git push origin $branch"
    exit 2
}
elseif ($localAhead -eq 0 -and $remoteAhead -gt 0) {
    $remoteFiles = git diff --name-only $branch "origin/$branch"
    $nonDocFiles = $remoteFiles | Where-Object { $_ -notmatch '^(docs/|AGENTS\.md|\.github/skills/|README\.md|ROADMAP\.md)' }

    if ($nonDocFiles) {
        Write-Output "⚠️ Cambios remotos incluyen código operativo:"
        $nonDocFiles | ForEach-Object { Write-Output $_ }
        Write-Output ""
        git log --oneline "$branch..origin/$branch"
        Write-Output ""
        Write-Output "Acción recomendada: git pull origin $branch (revisar cambios)"
        exit 3
    }

    Write-Output "✅ Pull automático de documentación..."
    Write-Output "Archivos a actualizar:"
    $remoteFiles | ForEach-Object { Write-Output $_ }
    git pull origin $branch --no-edit --quiet
    Write-Output "✅ Workspace sincronizado"
    exit 0
}
else {
    Write-Output "❌ Divergencia detectada: $localAhead commits locales, $remoteAhead remotos"
    Write-Output ""
    Write-Output "Commits locales:"
    git log --oneline "origin/$branch..$branch"
    Write-Output ""
    Write-Output "Commits remotos:"
    git log --oneline "$branch..origin/$branch"
    Write-Output ""
    Write-Output "Acción recomendada: git pull origin $branch (puede requerir merge)"
    exit 4
}
