$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(60))}
    catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch ended unexpectedly; no build started.'}
    if(-not $held){Write-Output 'UE batch busy; no build started.';exit 75}
    & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' *> 'D:/FPS3D/FPSGAME/SourceAssets/RifleReloadRecovery20260924/build_console.log'
    if($LASTEXITCODE -ne 0){throw "Editor build failed: $LASTEXITCODE"}
    Get-Content -LiteralPath 'D:/FPS3D/FPSGAME/SourceAssets/RifleReloadRecovery20260924/build_console.log' -Tail 14
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
