param(
    [string[]]$Profiles,
    [string[]]$Roots,
    [switch]$NoAutoDiscover
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Prefer models from providers backed by deeprouter.top / packyapi.com.
$preferredProviderPrefixes = @(
    'custom-deeprouter-top',
    'custom-www-packyapi-com'
)

# Quality-first ranking. If a model is healthy, choose the highest-ranked one.
$modelPriority = @(
    'custom-deeprouter-top-kiro/claude-opus-4-6-thinking',
    'custom-deeprouter-top/claude-opus-4-6-thinking',
    'custom-deeprouter-top-codex/claude-opus-4-6-thinking',
    'custom-www-packyapi-com/claude-opus-4-6',
    'custom-www-packyapi-com/gpt-5.3-codex-high',
    'custom-deeprouter-top-codex/gpt-5.2-xhigh',
    'custom-www-packyapi-com-2/gpt-5.2-xhigh',
    'custom-deeprouter-top/gemini-3.1-pro-preview',
    'custom-deeprouter-top-deepseek/deepseek-v3.2-thinking',
    'custom-deeprouter-top-deepseek/glm-5',
    'custom-deeprouter-top-deepseek/qwen3-next-80b-a3b-thinking'
)

# Collected during this run; included in stdout summary for cron run records.
$switchEvents = New-Object System.Collections.Generic.List[object]

function Write-TaskLog {
    param(
        [string]$LogPath,
        [string]$InstanceName,
        [string]$Message
    )

    $dir = Split-Path -Parent $LogPath
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }

    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz')
    $line = "[{0}] [{1}] {2}" -f $stamp, $InstanceName, $Message
    Add-Content -Path $LogPath -Value $line
}

function Get-OpenClawCommand {
    $candidates = @()

    if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
        $candidates += (Join-Path $env:APPDATA 'npm\openclaw.cmd')
    }

    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $candidates += (Join-Path $env:USERPROFILE 'AppData\Roaming\npm\openclaw.cmd')
    }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return 'openclaw'
}

function Invoke-OpenClaw {
    param(
        [string]$OpenClawCmd,
        [string]$Profile,
        [string[]]$Args
    )

    $fullArgs = @()
    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        $fullArgs += @('--profile', $Profile)
    }
    $fullArgs += $Args

    $output = ''
    $code = 1
    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
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
        CommandLine = ("{0} {1}" -f $OpenClawCmd, ($fullArgs -join ' '))
    }
}

function Parse-JsonFromMixedOutput {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    $start = $Text.IndexOf('{')
    $end = $Text.LastIndexOf('}')
    if ($start -lt 0 -or $end -le $start) {
        return $null
    }

    $jsonText = $Text.Substring($start, $end - $start + 1)
    try {
        return $jsonText | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Is-PreferredProviderModel {
    param([string]$ModelId)

    if ([string]::IsNullOrWhiteSpace($ModelId)) {
        return $false
    }

    $parts = $ModelId.Split('/', 2)
    if ($parts.Count -lt 2) {
        return $false
    }

    $provider = $parts[0]
    foreach ($prefix in $preferredProviderPrefixes) {
        if ($provider -like "$prefix*") {
            return $true
        }
    }

    return $false
}

function Get-ModelPriorityScore {
    param([string]$ModelId)

    for ($i = 0; $i -lt $modelPriority.Count; $i++) {
        if ($modelPriority[$i] -eq $ModelId) {
            return $i
        }
    }

    return 9999
}

function Is-LlmErrorMessage {
    param(
        [string]$Level,
        [string]$Message
    )

    if ([string]::IsNullOrWhiteSpace($Message)) {
        return $false
    }

    $agentTurnError = ($Message -match 'agent/embedded' -and $Message -match 'run agent end' -and $Message -match 'isError=true')
    $llmKeywords = ($Message -match '(authentication_error|invalid x-api-key|chat\.completions|completion|rate limit|overloaded|context length|too many tokens|model|provider|llm|openai|anthropic|gemini|timeout|429|5\d\d)')
    $warnOrError = ($Level -eq 'WARN' -or $Level -eq 'ERROR')

    return ($agentTurnError -or ($warnOrError -and $llmKeywords))
}

function Collect-LlmErrorsFromOpenClawLogs {
    param(
        [DateTimeOffset]$Since,
        [string]$OpenClawCmd,
        [string]$Profile,
        [string]$LogPath,
        [string]$InstanceName
    )

    $hits = New-Object System.Collections.Generic.List[object]
    $tail = Invoke-OpenClaw -OpenClawCmd $OpenClawCmd -Profile $Profile -Args @('logs', '--limit', '4000', '--json', '--max-bytes', '1000000')

    if ($tail.ExitCode -ne 0) {
        Write-TaskLog -LogPath $LogPath -InstanceName $InstanceName -Message ("Failed to read logs via CLI (exit={0}): {1}" -f $tail.ExitCode, $tail.Output.Trim())
        return $hits
    }

    $lines = $tail.Output -split "`r?`n"
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $entry = $null
        try {
            $entry = $line | ConvertFrom-Json
        }
        catch {
            continue
        }

        if ([string]$entry.type -ne 'log') {
            continue
        }

        if (-not $entry.time) {
            continue
        }

        try {
            $ts = [DateTimeOffset]::Parse([string]$entry.time)
        }
        catch {
            continue
        }

        if ($ts -lt $Since) {
            continue
        }

        $message = ((@([string]$entry.message, [string]$entry.raw) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join ' ')
        $level = ([string]$entry.level).ToUpperInvariant()

        if (Is-LlmErrorMessage -Level $level -Message $message) {
            $hits.Add([pscustomobject]@{
                Time = $ts
                Message = $message
            })
        }
    }

    return $hits
}

function Get-InstanceTargets {
    param(
        [string[]]$Profiles,
        [string[]]$Roots,
        [switch]$NoAutoDiscover
    )

    $items = New-Object System.Collections.Generic.List[object]
    $seen = @{}
    $homeDir = $env:USERPROFILE

    foreach ($root in @($Roots)) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $full = [System.IO.Path]::GetFullPath($root)
        if (-not (Test-Path $full)) { continue }
        if ($seen.ContainsKey($full.ToLowerInvariant())) { continue }
        $seen[$full.ToLowerInvariant()] = $true
        $items.Add($full)
    }

    foreach ($p in @($Profiles)) {
        if ([string]::IsNullOrWhiteSpace($p)) { continue }
        $name = $p.Trim()
        $candidate = $null
        if ($name -eq 'default') {
            $candidate = Join-Path $homeDir '.openclaw'
        }
        else {
            $candidate = Join-Path $homeDir ('.openclaw-{0}' -f $name)
        }
        if (-not (Test-Path $candidate)) { continue }
        $full = [System.IO.Path]::GetFullPath($candidate)
        if ($seen.ContainsKey($full.ToLowerInvariant())) { continue }
        $seen[$full.ToLowerInvariant()] = $true
        $items.Add($full)
    }

    if (-not $NoAutoDiscover) {
        $defaultRoot = Join-Path $homeDir '.openclaw'
        if (Test-Path $defaultRoot) {
            $full = [System.IO.Path]::GetFullPath($defaultRoot)
            if (-not $seen.ContainsKey($full.ToLowerInvariant())) {
                $seen[$full.ToLowerInvariant()] = $true
                $items.Add($full)
            }
        }

        $profileRoots = Get-ChildItem -Path $homeDir -Directory -Filter '.openclaw-*' -ErrorAction SilentlyContinue
        foreach ($dir in $profileRoots) {
            $full = [System.IO.Path]::GetFullPath($dir.FullName)
            if ($seen.ContainsKey($full.ToLowerInvariant())) { continue }
            $seen[$full.ToLowerInvariant()] = $true
            $items.Add($full)
        }
    }

    $targets = New-Object System.Collections.Generic.List[object]
    foreach ($root in $items) {
        $leaf = Split-Path -Leaf $root
        $profile = $null
        $name = 'default'
        if ($leaf -like '.openclaw-*') {
            $profile = $leaf.Substring(10)
            $name = $profile
        }
        $targets.Add([pscustomobject]@{
            Root = $root
            Profile = $profile
            Name = $name
            LogPath = Join-Path $root 'logs\llm-auto-heal.log'
        })
    }

    return $targets
}

function Process-Instance {
    param(
        [pscustomobject]$Instance,
        [string]$OpenClawCmd
    )

    $logPath = $Instance.LogPath
    $name = $Instance.Name
    $profile = $Instance.Profile
    $root = $Instance.Root

    try {
        $since = [DateTimeOffset]::Now.AddMinutes(-10)
        $recentErrors = @(Collect-LlmErrorsFromOpenClawLogs -Since $since -OpenClawCmd $OpenClawCmd -Profile $profile -LogPath $logPath -InstanceName $name)

        if ($recentErrors.Count -eq 0) {
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message 'No LLM errors in the last 10 minutes.'
            return $true
        }

        Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Detected {0} possible LLM error(s). Latest: {1}" -f $recentErrors.Count, $recentErrors[0].Message)

        $probe = Invoke-OpenClaw -OpenClawCmd $OpenClawCmd -Profile $profile -Args @('models', 'status', '--probe', '--json')
        if ($probe.ExitCode -ne 0) {
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Probe failed (exit={0}): {1}" -f $probe.ExitCode, $probe.Output.Trim())
            return $false
        }

        $probeObj = Parse-JsonFromMixedOutput -Text $probe.Output
        if (-not $probeObj) {
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Probe output is not valid JSON: {0}" -f $probe.Output.Trim())
            return $false
        }

        $currentModel = [string]$probeObj.resolvedDefault
        if ([string]::IsNullOrWhiteSpace($currentModel)) {
            $currentModel = [string]$probeObj.defaultModel
        }

        $okResults = @($probeObj.auth.probes.results | Where-Object {
                $_.status -eq 'ok' -and -not [string]::IsNullOrWhiteSpace([string]$_.model)
            })

        $preferredOk = @($okResults | Where-Object { Is-PreferredProviderModel -ModelId ([string]$_.model) })
        if ($preferredOk.Count -eq 0) {
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message 'No healthy preferred-provider model found from probe results.'
            return $false
        }

        $bestPreferred = @($preferredOk | Sort-Object `
            @{ Expression = { Get-ModelPriorityScore -ModelId ([string]$_.model) }; Ascending = $true }, `
            @{ Expression = { if ($null -eq $_.latencyMs) { 999999 } else { [int]$_.latencyMs } }; Ascending = $true }
        )

        $nextModel = [string]$bestPreferred[0].model
        if ([string]::IsNullOrWhiteSpace($nextModel)) {
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message 'Probe returned empty model id; aborting.'
            return $false
        }

        if ($nextModel -ne $currentModel) {
            $setResult = Invoke-OpenClaw -OpenClawCmd $OpenClawCmd -Profile $profile -Args @('models', 'set', $nextModel)
            if ($setResult.ExitCode -ne 0) {
                Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Failed to switch model to {0} (exit={1}): {2}" -f $nextModel, $setResult.ExitCode, $setResult.Output.Trim())
                return $false
            }
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Switched default model: {0} -> {1}" -f $currentModel, $nextModel)
            $script:switchEvents.Add([pscustomobject]@{
                Instance = $name
                FromModel = $currentModel
                ToModel = $nextModel
            })
        }
        else {
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Current model already best healthy: {0}" -f $currentModel)
        }

        $restart = Invoke-OpenClaw -OpenClawCmd $OpenClawCmd -Profile $profile -Args @('gateway', 'restart')
        if ($restart.ExitCode -eq 0) {
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message 'Gateway restarted by openclaw gateway restart.'
            return $true
        }

        $restartScript = Join-Path $root 'restart_openclaw_v2.ps1'
        if (Test-Path $restartScript) {
            $restartOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $restartScript 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0) {
                Write-TaskLog -LogPath $logPath -InstanceName $name -Message 'Gateway restarted by restart_openclaw_v2.ps1 fallback.'
                return $true
            }
            Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Fallback restart script failed (exit={0}): {1}" -f $LASTEXITCODE, $restartOutput.Trim())
            return $false
        }

        Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Gateway restart failed (exit={0}): {1}" -f $restart.ExitCode, $restart.Output.Trim())
        return $false
    }
    catch {
        $msg = [string]$_.Exception.Message
        if ([string]::IsNullOrWhiteSpace($msg)) {
            $msg = [string]$_
        }
        $line = $null
        if ($_.InvocationInfo) {
            $line = $_.InvocationInfo.ScriptLineNumber
        }
        Write-TaskLog -LogPath $logPath -InstanceName $name -Message ("Unhandled error at line {0}: {1}" -f $line, $msg)
        return $false
    }
}

$openclawCmd = Get-OpenClawCommand
$instances = @(Get-InstanceTargets -Profiles $Profiles -Roots $Roots -NoAutoDiscover:$NoAutoDiscover)

if ($instances.Count -eq 0) {
    $fallbackLog = Join-Path (Join-Path $env:USERPROFILE '.openclaw') 'logs\llm-auto-heal.log'
    Write-TaskLog -LogPath $fallbackLog -InstanceName 'global' -Message 'No OpenClaw instance directory found. Nothing to do.'
    exit 0
}

$failed = 0
foreach ($instance in $instances) {
    $ok = Process-Instance -Instance $instance -OpenClawCmd $openclawCmd
    if (-not $ok) {
        $failed++
    }
}

if ($failed -gt 0) {
    if ($switchEvents.Count -gt 0) {
        $switchSummary = ($switchEvents | ForEach-Object {
                "[{0}] {1} -> {2}" -f $_.Instance, $_.FromModel, $_.ToModel
            }) -join '; '
        Write-Output ("MODEL_SWITCHED: {0}" -f $switchSummary)
    }
    exit 1
}

if ($switchEvents.Count -gt 0) {
    $switchSummary = ($switchEvents | ForEach-Object {
            "[{0}] {1} -> {2}" -f $_.Instance, $_.FromModel, $_.ToModel
        }) -join '; '
    Write-Output ("MODEL_SWITCHED: {0}" -f $switchSummary)
}
else {
    Write-Output 'MODEL_SWITCHED: none'
}

exit 0
