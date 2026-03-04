param(
    [string]$Source = "C:\Users\lijing\.openclaw\workspace\skills",
    [string]$Message = "chore(skills): sync local skills",
    [switch]$NoPush,
    [switch]$AllowEmpty,
    [switch]$DryRun,
    [switch]$TagAfterPush,
    [string]$TagName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([string[]]$Args)
    $output = & git @Args 2>&1 | Out-String
    $code = $LASTEXITCODE
    return [pscustomobject]@{ Code = $code; Output = $output.TrimEnd() }
}

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
& git add skills .gitignore README.md 2>$null

# 3) Collect staged summary
$diffResult = Invoke-Git -Args @('diff', '--cached', '--name-status')
if ($diffResult.Code -ne 0) {
    throw "Failed to inspect staged changes: $($diffResult.Output)"
}
$changedLines = @($diffResult.Output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
$hasChanges = ($changedLines.Count -gt 0)

if (-not $hasChanges -and -not $AllowEmpty) {
    Write-Output "No changes to commit."
    exit 0
}

Write-Output "Staged changes:"
if ($changedLines.Count -gt 0) {
    $changedLines | ForEach-Object { Write-Output ("  " + $_) }
}
else {
    Write-Output "  (none)"
}

if ($DryRun) {
    Write-Output "Dry run mode: stop before commit/push."
    exit 0
}

# 4) Commit
if ($hasChanges) {
    & git commit -m $Message
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
}
else {
    & git commit --allow-empty -m $Message
    if ($LASTEXITCODE -ne 0) { throw "git commit --allow-empty failed" }
}

$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
$head = (& git rev-parse --short HEAD).Trim()

# 5) Push (optional)
if (-not $NoPush) {
    & git push origin $branch
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }
}

# 6) Optional tag
if ($TagAfterPush) {
    if ([string]::IsNullOrWhiteSpace($TagName)) {
        $TagName = "skills-" + (Get-Date).ToString("yyyyMMdd-HHmmss")
    }
    & git tag $TagName
    if ($LASTEXITCODE -ne 0) { throw "git tag failed: $TagName" }

    if (-not $NoPush) {
        & git push origin $TagName
        if ($LASTEXITCODE -ne 0) { throw "git push tag failed: $TagName" }
    }

    Write-Output "Tag created: $TagName"
}

Write-Output "Publish completed."
Write-Output "Branch: $branch"
Write-Output "Commit: $head"
