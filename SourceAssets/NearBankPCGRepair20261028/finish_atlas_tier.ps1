$ErrorActionPreference='Stop'
$atlasGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$atlasHeld=$false
try {
 $atlasHeld=$atlasGate.WaitOne([TimeSpan]::FromSeconds(900))
 if(-not $atlasHeld){throw 'UE queue occupied; atlas source files unchanged.'}
 if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Preserve active UE process; atlas source files unchanged.'}
 & 'C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' "$PSScriptRoot/prepare_atlas_tier.py"
 if($LASTEXITCODE -ne 0){throw 'Atlas tier preparation failed'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$PSScriptRoot/finish_atlas_tier.py" -unattended -nosplash -nosound -nullrhi '-ExecCmds=Editor.AsyncTextureCompilationMaxConcurrency 1,Editor.AsyncAssetCompilationMaxConcurrency 2,Editor.AsyncAssetCompilationMaxMemoryUsage 6' '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' "-abslog=$PSScriptRoot/atlas-tier-01.log" *> "$PSScriptRoot/atlas-tier-01-console.log"
 $atlasExit=$LASTEXITCODE
 @{exit_code=$atlasExit;game_run=$false;tests_run=$false;graphical_editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/atlas-tier-01.json" -Encoding utf8
 if($atlasExit -ne 0){throw "Atlas production returned $atlasExit"}
} finally {if($atlasHeld){$atlasGate.ReleaseMutex()};$atlasGate.Dispose()}
