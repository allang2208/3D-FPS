$ErrorActionPreference = 'Stop'
$captureRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$captureId = Get-Date -Format 'yyyyMMdd-HHmmss'
$captureDir = Join-Path $captureRoot ('Saved/SlateStall20260923/' + $captureId)
[IO.Directory]::CreateDirectory($captureDir) | Out-Null
$capturePython = Join-Path $captureDir 'start.py'
$captureTemplate = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'capture_slate_stall.py') -Raw
[IO.File]::WriteAllText($capturePython, $captureTemplate.Replace('__CAPTURE_ID__', $captureId), [Text.UTF8Encoding]::new($false))
$captureGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$captureHeld = $false
try {
    try { $captureHeld = $captureGate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $captureHeld = $true; throw 'Previous UE batch state unknown.' }
    if (-not $captureHeld) { throw 'UE batch busy.' }
    # The same PowerShell thread re-enters the mutex in the standard bridge.
    & (Join-Path $captureRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $capturePython -OutputFile (Join-Path $captureDir 'bridge.txt') -MaxOutputChars 1000
    if ($LASTEXITCODE -ne 0) { throw 'Capture setup failed.' }
    $captureWatch = [Diagnostics.Stopwatch]::StartNew()
    $captureStatePath = Join-Path $captureDir 'capture.json'
    while ($captureWatch.Elapsed.TotalSeconds -lt 120) {
        Start-Sleep -Milliseconds 500
        if (Test-Path -LiteralPath $captureStatePath) {
            try { $captureState = Get-Content -LiteralPath $captureStatePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { continue }
            if ($captureState.status -notin @('armed','recording')) {
                [pscustomobject]@{ Status=$captureState.status; Trace=$captureState.trace; ForegroundTicks=$captureState.foreground_ticks; BackgroundTicks=$captureState.background_ticks; Metadata=$captureStatePath } | Format-List
                if ($captureState.status -ne 'complete') { throw 'Capture did not complete normally; read metadata.' }
                return
            }
        }
    }
    throw 'Editor did not finish the armed capture; preserve its callback and inspect state before another capture.'
} finally {
    if ($captureHeld) { $captureGate.ReleaseMutex() }
    $captureGate.Dispose()
}
