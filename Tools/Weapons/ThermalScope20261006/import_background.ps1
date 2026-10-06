param([ValidateRange(1,3600)][int]$QueueWaitSeconds=60)
$ErrorActionPreference='Stop'
$thermalProject='D:/FPS3D/FPSGAME'
$thermalEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$thermalGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$thermalHeld=$false
try {
    try {$thermalHeld=$thermalGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))}
    catch [Threading.AbandonedMutexException] {$thermalHeld=$true}
    if(-not $thermalHeld){throw 'UE authoring batch busy; no commandlet started.'}
    $thermalEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if($thermalEditors.Count){throw 'FPSGAME is open; use the existing editor bridge.'}
    $thermalStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $thermalLog="$thermalProject/SourceAssets/ThermalScope20261006/import-$thermalStamp.log"
    $thermalConsole="$thermalProject/SourceAssets/ThermalScope20261006/import-$thermalStamp-console.txt"
    & $thermalEngine "$thermalProject/FPSGAME.uproject" -run=pythonscript "-script=$thermalProject/Tools/Weapons/ThermalScope20261006/import_model.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$thermalLog" *> $thermalConsole
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $thermalConsole -Tail 25;throw "Thermal model import failed: $thermalLog"}
    Write-Output "THERMAL_MODEL_SAVED $thermalLog"
} finally {
    if($thermalHeld){$thermalGate.ReleaseMutex()}
    $thermalGate.Dispose()
}
