param([ValidateRange(1,3600)][int]$QueueWaitSeconds=60)
$ErrorActionPreference='Stop'
$blessedProject='D:/FPS3D/FPSGAME'
$blessedEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$blessedGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$blessedHeld=$false
try {
    try { $blessedHeld=$blessedGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $blessedHeld=$true }
    if(-not $blessedHeld){throw 'UE authoring batch busy; no commandlet started.'}
    $blessedEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject' })
    if($blessedEditors.Count){throw 'FPSGAME is already open; use the existing editor bridge.'}
    $blessedStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $blessedLog="$blessedProject/Saved/BlessedLaser20261006/import-$blessedStamp.log"
    $blessedConsole="$blessedProject/Saved/BlessedLaser20261006/import-$blessedStamp-console.txt"
    & $blessedEngine "$blessedProject/FPSGAME.uproject" -run=pythonscript "-script=$blessedProject/Tools/Weapons/BlessedLaser20261006/save_all.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$blessedLog" *> $blessedConsole
    if($LASTEXITCODE -ne 0){ Get-Content -LiteralPath $blessedConsole -Tail 15; throw "Blessed laser import failed: $blessedLog" }
    Write-Output "BLESSED_EMITTER_ASSETS_SAVED $blessedLog"
} finally {
    if($blessedHeld){$blessedGate.ReleaseMutex()}
    $blessedGate.Dispose()
}
