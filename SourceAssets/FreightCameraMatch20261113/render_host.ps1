param([string]$SceneScript='capture.py')
$ErrorActionPreference='Stop'
$proj='D:\FPS3D\FPSGAME'
$hostRoot=Join-Path $PSScriptRoot 'RenderHost'
$leaf='L_FreightTransit_Theme_Subject.umap'
if (-not (Test-Path -LiteralPath "$hostRoot/FPSGAME.uproject")) {
    [IO.Directory]::CreateDirectory("$hostRoot/Content/GameMaps/Design") | Out-Null
    Copy-Item -LiteralPath "$proj/Config" -Destination "$hostRoot/Config" -Recurse
    foreach($key in @('Binaries','Plugins')){New-Item -ItemType Junction -Path "$hostRoot/$key" -Target "$proj/$key" | Out-Null}
    foreach($entry in Get-ChildItem -LiteralPath "$proj/Content" -Force){
        if($entry.Name -eq 'GameMaps'){continue}
        if($entry.PSIsContainer){New-Item -ItemType Junction -Path "$hostRoot/Content/$($entry.Name)" -Target $entry.FullName | Out-Null}
        else{Copy-Item -LiteralPath $entry.FullName -Destination "$hostRoot/Content/$($entry.Name)"}
    }
    foreach($entry in Get-ChildItem -LiteralPath "$proj/Content/GameMaps" -Force){
        if($entry.Name -eq 'Design'){continue}
        if($entry.PSIsContainer){New-Item -ItemType Junction -Path "$hostRoot/Content/GameMaps/$($entry.Name)" -Target $entry.FullName | Out-Null}
        else{New-Item -ItemType SymbolicLink -Path "$hostRoot/Content/GameMaps/$($entry.Name)" -Target $entry.FullName -ErrorAction SilentlyContinue | Out-Null}
    }
    Copy-Item -LiteralPath "$proj/Content/GameMaps/Design/$leaf" -Destination "$hostRoot/Content/GameMaps/Design/$leaf"
    Copy-Item -LiteralPath "$proj/FPSGAME.uproject" -Destination "$hostRoot/FPSGAME.uproject"
}
$exe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$log=Join-Path $PSScriptRoot ("render-$SceneScript-"+(Get-Date -Format yyyyMMdd-HHmmss)+'.log')
& $exe "$hostRoot/FPSGAME.uproject" '/Game/GameMaps/Design/L_FreightTransit_Theme_Subject' '-run=pythonscript' "-script=$PSScriptRoot/$SceneScript" '-AllowCommandletRendering' '-RenderOffscreen' '-d3d12' '-nosound' '-unattended' '-nop4' '-nosplash' '-NoAssetRegistryCacheWrite' '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' "-abslog=$log" *> "$log.stdout"
if($LASTEXITCODE -ne 0){throw "Render failed: $log"}
