param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [string]$Owner = "unknown",
    [string]$Platform = "windows"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tasksRoot = Join-Path $repoRoot "tasks"
$templateRoot = Join-Path $tasksRoot "_template"
$taskRoot = Join-Path $tasksRoot $Name

if (Test-Path $taskRoot) {
    throw "Task already exists: $taskRoot"
}

if (-not (Test-Path $templateRoot)) {
    throw "Template folder missing: $templateRoot"
}

Copy-Item -Path $templateRoot -Destination $taskRoot -Recurse -Force

# Ensure common structure exists
New-Item -ItemType Directory -Path (Join-Path $taskRoot "scripts") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $taskRoot "docs") -Force | Out-Null

# Fill metadata
$metaPath = Join-Path $taskRoot "task.meta.json"
if (Test-Path $metaPath) {
    $meta = @{
        name = $Name
        status = "draft"
        owner = $Owner
        platform = @($Platform)
        entrypoint = "scripts/<entry-script>.ps1"
        description = "TODO"
        tags = @("automation")
        updatedAt = (Get-Date).ToString("yyyy-MM-dd")
    }
    $meta | ConvertTo-Json -Depth 5 | Set-Content -Path $metaPath -Encoding UTF8
}

Write-Output "Created task scaffold: $taskRoot"
Write-Output "Next: edit README.md + task.meta.json, then add row to tasks/index.md"
