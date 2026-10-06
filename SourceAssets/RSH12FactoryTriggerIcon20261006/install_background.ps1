$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject 'SourceAssets/RSH12FactoryTriggerIcon20261006'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if ($taskEditors.Count -gt 0) {throw 'FPSGAME is running; no loaded assets were overwritten.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskOutput/import_icon.py" `
        -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen `
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
        "-abslog=$taskOutput/Import-commandlet.log" *> "$taskOutput/Import-console.log"
    if ($LASTEXITCODE -ne 0) {throw "RSH factory trigger icon import failed ($LASTEXITCODE)."}
    Write-Output 'RSH_FACTORY_TRIGGER_ICON_IMPORT_COMPLETE'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
