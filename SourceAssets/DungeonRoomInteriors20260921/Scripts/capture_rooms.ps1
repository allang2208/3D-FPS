$ErrorActionPreference = 'Stop'
$dungeonRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $dungeonRoot 'Receipts/room-capture-state.json'
$receiptPath = Join-Path $dungeonRoot ('Receipts/bridge-room-capture-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.txt')
# The bridge and this wrapper share the same re-entrant Windows mutex. Keep it
# until the finite rendering callback finishes, so another bridge call cannot
# change the active map halfway through the user's requested screenshots.
$captureGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$captureHeld = $false
try {
    $captureHeld = $captureGate.WaitOne([TimeSpan]::FromSeconds(180))
    if (-not $captureHeld) { throw 'Capture batch could not obtain the UE bridge gate.' }
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript (Join-Path $PSScriptRoot 'capture_rooms.py') -OutputFile $receiptPath -MaxOutputChars 3000
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $captureDeadline = [DateTime]::UtcNow.AddMinutes(4)
    do {
        Start-Sleep -Seconds 2
        $captureState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($captureState.status -eq 'complete') { $captureState | ConvertTo-Json -Depth 5; exit 0 }
        if ($captureState.status -eq 'failed') { throw $captureState.error }
    } while ([DateTime]::UtcNow -lt $captureDeadline)
    throw 'Capture is still pending; preserve its state and do not blindly rerun.'
} finally {
    if ($captureHeld) { $captureGate.ReleaseMutex() }
    $captureGate.Dispose()
}
