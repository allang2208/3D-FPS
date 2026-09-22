param([ValidatePattern('^[a-z0-9_]+$')][string]$Label='before_clean')
$ErrorActionPreference='Stop'
$witchRoot='D:/FPS3D/FPSGAME'
$witchOut=Join-Path $witchRoot 'SourceAssets/WitchRebuilt20260921/Revision06'
$witchReport=Join-Path $witchOut ('performance_'+$Label+'.json')
if (Test-Path -LiteralPath $witchReport) { throw 'Use a fresh capture label; existing results are preserved.' }
$witchDriver=Join-Path $witchOut ('run_'+$Label+'.py')
$witchCode=@"
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/Tools/WitchRebuilt/run_profile06.py')
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p),'WITCH_PROFILE_LABEL':'$Label'})
"@
[IO.File]::WriteAllText($witchDriver,$witchCode,[Text.UTF8Encoding]::new($false))
# Reuse the bridge's same recursive Windows mutex for this asynchronous capture.
# The editor keeps ticking while the owning batch awaits its completion file.
$witchCaptureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$witchHeld=$false
try {
    $witchHeld=$witchCaptureGate.WaitOne([TimeSpan]::FromSeconds(300))
    if (!$witchHeld) { throw 'Editor capture window is busy; no capture started.' }
    & (Join-Path $witchRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $witchDriver -OutputFile (Join-Path $witchOut ('capture_'+$Label+'.txt')) -MaxOutputChars 1800 -QueueWaitSeconds 300
    if ($LASTEXITCODE -ne 0) { throw 'Capture setup failed.' }
    $witchDeadline=[DateTime]::UtcNow.AddSeconds(170)
    while (!(Test-Path -LiteralPath $witchReport)) {
        if ([DateTime]::UtcNow -gt $witchDeadline) { throw 'Capture completion timed out; preserve the editor state.' }
        Start-Sleep -Milliseconds 500
    }
    Get-Content -Raw -LiteralPath $witchReport
} finally {
    if ($witchHeld) {$witchCaptureGate.ReleaseMutex()}
    $witchCaptureGate.Dispose()
}
