$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    $held = $gate.WaitOne([TimeSpan]::FromSeconds(60))
    if (-not $held) { throw 'UE bridge busy; no capture started' }
    $receipt = Join-Path $reviewRoot ('Receipts/capture-bridge-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.txt')
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript (Join-Path $PSScriptRoot 'capture_materials.py') -OutputFile $receipt -MaxOutputChars 1600
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    do {
        Start-Sleep -Seconds 2
        $state = Get-Content (Join-Path $reviewRoot 'Receipts/capture-state.json') -Raw | ConvertFrom-Json
        if ($state.status -eq 'complete') { Write-Output 'WALL_REVIEW_CAPTURE_COMPLETE'; exit 0 }
        if ($state.status -eq 'failed') { throw $state.error }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Capture callback still pending; preserve state'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
