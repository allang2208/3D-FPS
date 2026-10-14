$ErrorActionPreference='Stop'
$gardenProject='D:/FPS3D/FPSGAME'
$gardenRoot="$gardenProject/SourceAssets/EcologyGardener20261014/V02"
$gardenScript="$gardenProject/Tools/EcologyGardener/import_v02.py"
$gardenMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$gardenHeld=$false
$gardenPreviousSdk=$env:UE_SKIP_UBT_SDK_SETUP
$gardenReceipt=[ordered]@{stage='waiting';native_build_required=$false;runtime_tested=$false;rendered=$false}
try {
    while (-not $gardenHeld) {
        try {$gardenHeld=$gardenMutex.WaitOne(5000)}catch [Threading.AbandonedMutexException] {$gardenHeld=$true}
        if (-not $gardenHeld) {continue}
        $gardenProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe'")
        $gardenEditors=@($gardenProcesses|Where-Object {$_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'FPSGAME.uproject'})
        if ($gardenEditors|Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {throw 'Preserve the running project editor; import through the existing MCP bridge.'}
        $gardenBuilds=@($gardenProcesses|Where-Object {$_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if (-not $gardenEditors.Count -and -not $gardenBuilds.Count) {break}
        $gardenMutex.ReleaseMutex();$gardenHeld=$false
        Start-Sleep -Seconds 10
    }
    $gardenLog="$gardenRoot/Logs/import-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "GARDENER_V02_IMPORT_STARTED LOG=$gardenLog"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$gardenProject/FPSGAME.uproject" '-run=pythonscript' "-script=$gardenScript" '-unattended' '-nop4' '-nosplash' '-d3d12' '-sm6' '-RenderOffscreen' '-AllowCommandletRendering' '-nosound' "-abslog=$gardenLog" *> "$gardenLog.stdout"
    $gardenReceipt.import=@{exit_code=$LASTEXITCODE;log=$gardenLog}
    if ($LASTEXITCODE -ne 0) {throw "Asset import failed: $gardenLog"}
    $gardenAssets=Get-Content "$gardenRoot/ue_delivery.json" -Raw|ConvertFrom-Json
    if ($gardenAssets.stage -ne 'assets_saved') {throw 'The import did not report saved assets.'}
    $gardenReceipt.stage='imported_saved';$gardenReceipt.assets=$gardenAssets;$gardenReceipt.finished=(Get-Date -Format o)
    $gardenReceipt|ConvertTo-Json -Depth 8|Set-Content "$gardenRoot/delivery.json" -Encoding utf8
    Write-Output 'GARDENER_V02_DELIVERED'
} catch {
    $gardenReceipt.stage='blocked_or_failed';$gardenReceipt.error=$_.Exception.Message
    $gardenReceipt|ConvertTo-Json -Depth 8|Set-Content "$gardenRoot/delivery.json" -Encoding utf8
    throw
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$gardenPreviousSdk
    if ($gardenHeld) {$gardenMutex.ReleaseMutex()}
    $gardenMutex.Dispose()
}
