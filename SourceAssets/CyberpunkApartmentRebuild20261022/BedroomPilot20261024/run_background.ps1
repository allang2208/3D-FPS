param([string]$Script='publish.py',[string]$Run='publish-01',[switch]$CompileMaterials,[int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$bedroomRoot=$PSScriptRoot
$bedroomGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bedroomHeld=$false
try {
    $bedroomHeld=$bedroomGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
    if(-not $bedroomHeld){throw 'UE publication window busy; no request sent.'}
    $bedroomFlag=if($CompileMaterials -or $Script -in @('build_assets.py','publish.py')){'-AllowCommandletRendering'}else{'-nullrhi'}
    # All writes belong to this pilot's new asset folder and independent map.
    # Existing apartment packages are read-only dependencies, including during PIE.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$bedroomRoot/$Script" -unattended -nosplash -nosound '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' $bedroomFlag "-abslog=$bedroomRoot/$Run.log" *> "$bedroomRoot/$Run-console.log"
    $bedroomExit=$LASTEXITCODE
    @{exit_code=$bedroomExit;script=$Script;game_run=$false;interactive_editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$bedroomRoot/$Run.json" -Encoding utf8
    if($bedroomExit -ne 0){throw "Bedroom commandlet failed; see $bedroomRoot/$Run.log"}
    Write-Output "Bedroom production batch completed: $Script"
} finally {
    if($bedroomHeld){$bedroomGate.ReleaseMutex()}
    $bedroomGate.Dispose()
}
