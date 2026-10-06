$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject 'SourceAssets/RSH12MuzzleBrake20261005'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if (-not $taskHeld) {throw 'The UE asset batch is busy; installation has not started.'}
    $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if ($taskEditors.Count -gt 0) {throw 'FPSGAME is already running; no process was stopped and no assets were overwritten.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskOutput/import_all.py" `
        -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen `
        "-abslog=$taskOutput/Import-commandlet.log" *> "$taskOutput/Import-console.log"
    if ($LASTEXITCODE -ne 0) {throw "RSH muzzle brake import failed ($LASTEXITCODE); see Import-commandlet.log."}
    Write-Output 'RSH_BRAKE_ASSETS_SAVED'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
