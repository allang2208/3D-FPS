param([ValidateRange(1,3600)][int]$QueueWaitSeconds=60)
$ErrorActionPreference='Stop'
$mountProject='D:/FPS3D/FPSGAME'
$mountEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$mountGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$mountHeld=$false
try {
    try {$mountHeld=$mountGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))}
    catch [Threading.AbandonedMutexException] {$mountHeld=$true}
    if(-not $mountHeld){throw 'UE authoring batch busy; no commandlet started.'}
    $mountEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if($mountEditors.Count){throw 'FPSGAME is open; use the existing editor bridge.'}
    $mountStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $mountLog="$mountProject/Saved/BlessedLaser20261006/mount-import-$mountStamp.log"
    $mountConsole="$mountProject/Saved/BlessedLaser20261006/mount-import-$mountStamp-console.txt"
    & $mountEngine "$mountProject/FPSGAME.uproject" -run=pythonscript "-script=$mountProject/Tools/Weapons/BlessedLaser20261006/import_mounts_v2.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$mountLog" *> $mountConsole
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $mountConsole -Tail 25;throw "Mount import failed: $mountLog"}
    Write-Output "BLESSED_MOUNTS_SAVED $mountLog"
} finally {
    if($mountHeld){$mountGate.ReleaseMutex()}
    $mountGate.Dispose()
}
