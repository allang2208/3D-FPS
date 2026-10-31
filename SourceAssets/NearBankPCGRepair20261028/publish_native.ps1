$ErrorActionPreference='Stop'
$nativeGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$nativeHeld=$false
try {
 $nativeHeld=$nativeGate.WaitOne([TimeSpan]::FromSeconds(900))
 if(-not $nativeHeld){throw 'UE production queue occupied; no project assets changed.'}
 $nativeProcesses=@(Get-CimInstance Win32_Process)
 if($nativeProcesses | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Preserve existing UE process. Publication deferred.'}
 & 'C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' "$PSScriptRoot/stage_assets.py"
 if($LASTEXITCODE -ne 0){throw 'Selected asset migration did not complete.'}
 & 'C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' "$PSScriptRoot/compose_publish.py"
 if($LASTEXITCODE -ne 0){throw 'Street composition did not complete.'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$PSScriptRoot/publish_native.py" -unattended -nosplash -nosound -nullrhi '-ExecCmds=Editor.AsyncTextureCompilationMaxConcurrency 1,Editor.AsyncAssetCompilationMaxConcurrency 2,Editor.AsyncAssetCompilationMaxMemoryUsage 6' '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' "-abslog=$PSScriptRoot/native-publish-01.log" *> "$PSScriptRoot/native-publish-01-console.log"
 $nativeExit=$LASTEXITCODE
 @{exit_code=$nativeExit;game_run=$false;tests_run=$false;graphical_editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/native-publish-01.json" -Encoding utf8
 if($nativeExit -ne 0){throw "Native district publication returned $nativeExit"}
} finally {if($nativeHeld){$nativeGate.ReleaseMutex()};$nativeGate.Dispose()}
