param([switch]$ImportOnly)
$ErrorActionPreference='Stop'
$gardenProject='D:/FPS3D/FPSGAME'
$gardenRoot="$gardenProject/SourceAssets/EcologyGardener20261014/V01"
$gardenEngine='E:/Program Files (x86)/UE_5.8'
$gardenMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$gardenHeld=$false
$gardenOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
$gardenResults=[ordered]@{stage='waiting';builds=@();runtime_tested=$false;multiplayer_tested=$false;rendered=$false}
try {
    if ($ImportOnly) {
        $gardenPrevious=Get-Content "$gardenRoot/delivery.json" -Raw|ConvertFrom-Json
        $gardenResults.builds=@($gardenPrevious.builds)
        if ($gardenResults.builds.Count -ne 2 -or @($gardenResults.builds|Where-Object {$_.exit_code -ne 0}).Count) {throw 'ImportOnly requires the completed native build receipts.'}
    }
    $gardenAnnounced=$false
    while (-not $gardenHeld) {
        try {$gardenHeld=$gardenMutex.WaitOne(5000)}catch [Threading.AbandonedMutexException] {$gardenHeld=$true}
        if (-not $gardenHeld) {continue}
        $gardenProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe'")
        $gardenEditors=@($gardenProcesses|Where-Object {$_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'FPSGAME.uproject'})
        if ($gardenEditors|Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {throw 'Preserve the running FPSGAME editor; close it before linking.'}
        $gardenBuilds=@($gardenProcesses|Where-Object {$_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if (-not $gardenEditors.Count -and -not $gardenBuilds.Count) {break}
        $gardenMutex.ReleaseMutex();$gardenHeld=$false
        if (-not $gardenAnnounced) {Write-Output 'Waiting for the active project build/commandlet.';$gardenAnnounced=$true}
        Start-Sleep -Seconds 10
    }
    $gardenTargets=if ($ImportOnly) {@()} else {@('FPSGAMEEditor','FPSGAME')}
    foreach ($gardenTarget in $gardenTargets) {
        $gardenLog="$gardenRoot/Logs/build-$gardenTarget-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
        Write-Output "GARDENER_BUILD_STARTED $gardenTarget LOG=$gardenLog"
        & "$gardenEngine/Engine/Build/BatchFiles/Build.bat" $gardenTarget Win64 Development "-Project=$gardenProject/FPSGAME.uproject" '-NoHotReloadFromIDE' '-WaitMutex' *> $gardenLog
        $gardenCode=$LASTEXITCODE
        $gardenResults.builds+=@{target=$gardenTarget;exit_code=$gardenCode;log=$gardenLog}
        $gardenResults.stage='building';$gardenResults|ConvertTo-Json -Depth 5|Set-Content "$gardenRoot/delivery.json" -Encoding utf8
        Write-Output "GARDENER_BUILD_FINISHED $gardenTarget EXIT=$gardenCode"
        if ($gardenCode -ne 0) {throw "Native build failed: $gardenLog"}
    }
    $gardenLog="$gardenRoot/Logs/import-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "GARDENER_IMPORT_STARTED LOG=$gardenLog"
    & "$gardenEngine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$gardenProject/FPSGAME.uproject" '-run=pythonscript' "-script=$gardenProject/Tools/EcologyGardener/import_assets.py" '-unattended' '-nop4' '-nosplash' '-d3d12' '-sm6' '-RenderOffscreen' '-AllowCommandletRendering' '-nosound' "-abslog=$gardenLog" *> "$gardenLog.stdout"
    $gardenCode=$LASTEXITCODE
    $gardenResults.import=@{exit_code=$gardenCode;log=$gardenLog}
    if ($gardenCode -ne 0) {throw "Asset import failed: $gardenLog"}
    $gardenAssets=Get-Content "$gardenRoot/ue_delivery.json" -Raw|ConvertFrom-Json
    if ($gardenAssets.stage -ne 'assets_saved') {throw 'The import did not report saved assets.'}
    $gardenResults.assets=$gardenAssets;$gardenResults.stage='built_imported_saved';$gardenResults.finished=(Get-Date -Format o)
    $gardenResults|ConvertTo-Json -Depth 8|Set-Content "$gardenRoot/delivery.json" -Encoding utf8
    Write-Output "GARDENER_DELIVERED $gardenRoot/delivery.json"
} catch {
    $gardenResults.stage='blocked_or_failed';$gardenResults.error=$_.Exception.Message
    $gardenResults|ConvertTo-Json -Depth 8|Set-Content "$gardenRoot/delivery.json" -Encoding utf8
    throw
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$gardenOldSdk
    if ($gardenHeld) {$gardenMutex.ReleaseMutex()}
    $gardenMutex.Dispose()
}
