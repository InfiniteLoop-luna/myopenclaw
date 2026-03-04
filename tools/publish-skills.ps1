param(
    [string]$Source = "C:\Users\lijing\.openclaw\workspace\skills",
    [string]$Message = "chore(skills): sync local skills",
    [switch]$NoPush,
    [switch]$AllowEmpty
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$syncScript = Join-Path $PSScriptRoot "sync-skills.ps1"
if (-not (Test-Path $syncScript)) {
    throw "Missing sync script: $syncScript"
}

# 1) Sync local skills into repo/skills
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $syncScript -Source $Source -RepoSkillsPath ".\skills"
if ($LASTEXITCODE -ne 0) {
    throw "Sync script failed with exit code $LASTEXITCODE"
}

# 2) Stage
& git add skills .gitignore README.md

# 3) Detect changes
& git diff --cached --quiet
$hasChanges = ($LASTEXITCODE -ne 0)

if (-not $hasChanges -and -not $AllowEmpty) {
    Write-Output "No changes to commit."
    exit 0
}

# 4) Commit
if ($hasChanges) {
    & git commit -m $Message
}
else {
    & git commit --allow-empty -m $Message
}

# 5) Push (optional)
if (-not $NoPush) {
    $branch = (& git rev-parse --abbrev-ref HEAD).Trim()
    & git push origin $branch
}

Write-Output "Publish completed."
