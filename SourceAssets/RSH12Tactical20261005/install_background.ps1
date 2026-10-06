$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject 'SourceAssets/RSH12Tactical20261005'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if ($taskEditors.Count -gt 0) {throw 'FPSGAME is already running; no process was stopped and no assets were overwritten.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskOutput/import_assets.py" `
        -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen `
        "-abslog=$taskOutput/Import-commandlet.log" *> "$taskOutput/Import-console.log"
    if ($LASTEXITCODE -ne 0) {throw "RSH tactical device import failed ($LASTEXITCODE); see Import-commandlet.log."}
    Write-Output 'RSH_TACTICAL_ASSETS_SAVED'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
