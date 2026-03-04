param(
    [string]$Source = "C:\Users\lijing\.openclaw\workspace\skills",
    [string]$RepoSkillsPath = ".\skills"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $Source)) {
    throw "Source not found: $Source"
}

if (Test-Path $RepoSkillsPath) {
    Remove-Item -Recurse -Force $RepoSkillsPath
}
New-Item -ItemType Directory -Path $RepoSkillsPath -Force | Out-Null
Copy-Item -Path (Join-Path $Source '*') -Destination $RepoSkillsPath -Recurse -Force

Get-ChildItem -Path $RepoSkillsPath -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $RepoSkillsPath -Recurse -File -Include '*.pyc','*.pyo' -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Output "Skills synced to $RepoSkillsPath"
