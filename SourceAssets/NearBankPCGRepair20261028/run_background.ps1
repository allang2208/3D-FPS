param([string]$Script='build_assets.py',[string]$Run='assets-01',[switch]$Render,[string]$ProjectPath='D:/FPS3D/FPSGAME/FPSGAME.uproject')
$ErrorActionPreference='Stop'
$nearBankGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$nearBankHeld=$false
try {
 $nearBankHeld=$nearBankGate.WaitOne([TimeSpan]::FromSeconds(900))
 if(-not $nearBankHeld){throw 'UE batch occupied. No commandlet started.'}
 $nearBankProcesses=@(Get-CimInstance Win32_Process)
 $nearBankProjectFull=[IO.Path]::GetFullPath($ProjectPath).Replace('\','/')
 $nearBankOwnHost=[IO.Path]::GetFullPath("$PSScriptRoot/AuthoringHost/CityAuthoring.uproject").Replace('\','/')
 $nearBankPublicationHost=[IO.Path]::GetFullPath("$PSScriptRoot/PublicationHost/FPSGAME.uproject").Replace('\','/')
 $nearBankIsolated=($nearBankProjectFull -eq $nearBankOwnHost) -or ($nearBankProjectFull -eq $nearBankPublicationHost) -or ($nearBankProjectFull -eq 'D:/FPS3D/FPSGAME/SourceAssets/CitySamplePCGResearch20261028/ReadHost/CityReadHost.uproject')
 if($nearBankProcesses | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'UnrealEditor.exe' -and -not $nearBankIsolated) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Preserve existing UE process; use its editor bridge when applicable.'}
 $nearBankRhi=if($Render){'-AllowCommandletRendering'}else{'-nullrhi'}
 $nearBankRenderArgs=if($Render){@('-ExecCmds=Editor.AsyncTextureCompilationMaxConcurrency 1,Editor.AsyncAssetCompilationMaxConcurrency 2,Editor.AsyncAssetCompilationMaxMemoryUsage 8','-ini:Engine:[DevOptions.Shaders]:ShaderCompilerCoreCountThreshold=0','-ini:Engine:[DevOptions.Shaders]:PercentageUnusedShaderCompilingThreads=85')}else{@()}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $ProjectPath -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -nosplash -nosound $nearBankRhi @nearBankRenderArgs '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' "-abslog=$PSScriptRoot/$Run.log" *> "$PSScriptRoot/$Run-console.log"
 $nearBankExit=$LASTEXITCODE
 @{exit_code=$nearBankExit;script=$Script;game_run=$false;tests_run=$false;graphical_editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/$Run.json" -Encoding utf8
 if($nearBankExit -ne 0){throw "Near-bank production returned $nearBankExit; see $Run.log"}
} finally {if($nearBankHeld){$nearBankGate.ReleaseMutex()};$nearBankGate.Dispose()}
