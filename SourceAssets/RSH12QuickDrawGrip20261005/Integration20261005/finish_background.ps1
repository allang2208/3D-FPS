param()
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject 'SourceAssets/RSH12QuickDrawGrip20261005/Integration20261005'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    Write-Output 'Waiting for the existing UE authoring/build batch to finish.'
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    while ($true) {
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
        if ($taskEditors | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {throw 'FPSGAME editor is open; no editor was stopped.'}
        $taskBuilders=@(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if ($taskEditors.Count -eq 0 -and $taskBuilders.Count -eq 0) {break}
        Start-Sleep -Seconds 15
    }
    Write-Output 'Saving quick-draw grip assets and icon with a background commandlet.'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskOutput/import_all.py" `
        -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen "-abslog=$taskOutput/Import-commandlet.log" *> "$taskOutput/Import-console.log"
    if ($LASTEXITCODE -ne 0) {throw "Asset import failed ($LASTEXITCODE); see Import-commandlet.log."}
    & py -3.11 "$taskOutput/publish_catalog.py"
    if ($LASTEXITCODE -ne 0) {throw "Catalog publication failed ($LASTEXITCODE)."}
    Write-Output 'RSH_QUICKDRAW_GRIP_ASSETS_AND_CATALOG_SAVED'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
& "$taskOutput/build_editor.ps1"
