param(
    [string]$ScriptPath = "$env:USERPROFILE\.openclaw\scripts\llm-auto-heal.ps1",
    [string]$JobName = "OpenClaw LLM Auto Heal",
    [int]$IntervalMinutes = 30,
    [int]$TimeoutSeconds = 900,
    [string]$AgentId = "main",
    [string]$SessionTarget = "isolated",
    [string]$Profile,
    [switch]$DisableWindowsTask
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-OpenClawCmd {
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
        $candidates += (Join-Path $env:APPDATA "npm\openclaw.cmd")
    }
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $candidates += (Join-Path $env:USERPROFILE "AppData\Roaming\npm\openclaw.cmd")
    }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return "openclaw"
}

function Invoke-OpenClaw {
    param(
        [string]$OpenClawCmd,
        [string[]]$CliArgs,
        [string]$Profile
    )

    $fullArgs = @()
    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $fullArgs += @("--profile", $Profile)
    }
    $fullArgs += $CliArgs

    $output = ""
    $code = 1
    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $output = & $OpenClawCmd @fullArgs 2>&1 | Out-String
            $code = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $prev
        }
    }
    catch {
        $msg = [string]$_.Exception.Message
        if ([string]::IsNullOrWhiteSpace($msg)) {
            $msg = [string]$_
        }
        $output = "native command failed: $msg"
        $code = 1
    }

    return [pscustomobject]@{
        ExitCode = $code
        Output = $output
        CommandLine = "{0} {1}" -f $OpenClawCmd, ($fullArgs -join " ")
    }
}

function Parse-JsonFromMixedOutput {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    # Fast path: whole text is valid JSON.
    try {
        return $Text | ConvertFrom-Json
    }
    catch {
    }

    # Fallback: find the first parseable JSON object block.
    for ($start = 0; $start -lt $Text.Length; $start++) {
        if ($Text[$start] -ne '{') { continue }
        for ($end = $Text.Length - 1; $end -gt $start; $end--) {
            if ($Text[$end] -ne '}') { continue }
            $candidate = $Text.Substring($start, $end - $start + 1)
            try {
                return $candidate | ConvertFrom-Json
            }
            catch {
            }
        }
    }

    return $null
}

if (-not (Test-Path $ScriptPath)) {
    throw "Script not found: $ScriptPath"
}

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

if ($TimeoutSeconds -lt 30) {
    throw "TimeoutSeconds should be >= 30"
}

$openclaw = Get-OpenClawCmd
$every = "{0}m" -f $IntervalMinutes
$message = "Run auto-heal check: inspect last 10 minutes for LLM/model errors; if errors are found, execute powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ScriptPath; print concise summary and model switch result."

# Read current jobs first.
$listResult = Invoke-OpenClaw -OpenClawCmd $openclaw -Profile $Profile -CliArgs @("cron", "list", "--json")
if ($listResult.ExitCode -ne 0) {
    throw "Failed to list cron jobs: $($listResult.Output.Trim())"
}

$listObj = Parse-JsonFromMixedOutput -Text $listResult.Output
if (-not $listObj) {
    throw "Cannot parse cron list output as JSON. Raw:`n$($listResult.Output)"
}

$existing = @($listObj.jobs | Where-Object { $_.name -eq $JobName })
if ($existing.Count -gt 0) {
    $jobId = [string]$existing[0].id
    $editArgs = @(
        "cron", "edit", $jobId,
        "--every", $every,
        "--timeout-seconds", [string]$TimeoutSeconds,
        "--agent", $AgentId,
        "--session", $SessionTarget,
        "--message", $message,
        "--no-deliver",
        "--enable"
    )
    $editResult = Invoke-OpenClaw -OpenClawCmd $openclaw -Profile $Profile -CliArgs $editArgs
    if ($editResult.ExitCode -ne 0) {
        throw "Failed to edit cron job ${jobId}: $($editResult.Output.Trim())"
    }
}
else {
    $addArgs = @(
        "cron", "add",
        "--name", $JobName,
        "--description", "LLM auto-heal every $IntervalMinutes minutes",
        "--every", $every,
        "--agent", $AgentId,
        "--session", $SessionTarget,
        "--message", $message,
        "--no-deliver",
        "--timeout-seconds", [string]$TimeoutSeconds,
        "--json"
    )
    $addResult = Invoke-OpenClaw -OpenClawCmd $openclaw -Profile $Profile -CliArgs $addArgs
    if ($addResult.ExitCode -ne 0) {
        throw "Failed to add cron job: $($addResult.Output.Trim())"
    }
}

# Re-read and print final status.
$finalListResult = Invoke-OpenClaw -OpenClawCmd $openclaw -Profile $Profile -CliArgs @("cron", "list", "--json")
if ($finalListResult.ExitCode -ne 0) {
    throw "Failed to list cron jobs after update: $($finalListResult.Output.Trim())"
}

$finalObj = Parse-JsonFromMixedOutput -Text $finalListResult.Output
if (-not $finalObj) {
    throw "Cannot parse final cron list output as JSON. Raw:`n$($finalListResult.Output)"
}

$finalJob = @($finalObj.jobs | Where-Object { $_.name -eq $JobName } | Select-Object -First 1)
if ($finalJob.Count -eq 0) {
    throw "Job '$JobName' not found after creation/update."
}

$job = $finalJob[0]
$summary = [pscustomobject]@{
    name = $job.name
    id = $job.id
    enabled = $job.enabled
    everyMs = $job.schedule.everyMs
    timeoutSeconds = $job.payload.timeoutSeconds
    nextRunAtMs = $job.state.nextRunAtMs
    lastRunStatus = $job.state.lastRunStatus
}
Write-Output "OpenClaw cron job is ready:"
$summary | ConvertTo-Json

if ($DisableWindowsTask) {
    $taskMatches = Get-ScheduledTask | Where-Object {
        $task = $_
        $matched = $false

        foreach ($action in @($task.Actions)) {
            if ($null -eq $action) { continue }

            $props = @($action.PSObject.Properties.Name)
            $exec = if ($props -contains 'Execute') { [string]$action.Execute } else { '' }
            $args = if ($props -contains 'Arguments') { [string]$action.Arguments } else { '' }

            if (($exec -match 'powershell') -and ($args -match [regex]::Escape($ScriptPath))) {
                $matched = $true
                break
            }
        }

        $matched
    }

    foreach ($task in $taskMatches) {
        Disable-ScheduledTask -TaskPath $task.TaskPath -TaskName $task.TaskName | Out-Null
        Write-Output ("Disabled Windows task: {0}{1}" -f $task.TaskPath, $task.TaskName)
    }
}
