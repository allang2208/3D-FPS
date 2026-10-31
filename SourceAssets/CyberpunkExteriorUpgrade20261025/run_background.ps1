param([string]$Script='read_sources.py',[string]$Run='sources-01',[switch]$Render,[int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$exteriorRoot=$PSScriptRoot
$exteriorGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$exteriorHeld=$false
try {
    $exteriorHeld=$exteriorGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
    if(-not $exteriorHeld){throw 'UE production window busy; no commandlet started.'}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Existing editor must retain its loaded assets; use the project bridge.'}
    $exteriorRhi=if($Render){'-AllowCommandletRendering'}else{'-nullrhi'}
    $exteriorAuthoringArgs=if($Render){@('-ExecCmds=Editor.AsyncTextureCompilationMaxConcurrency 1,Editor.AsyncAssetCompilationMaxConcurrency 2,Editor.AsyncAssetCompilationMaxMemoryUsage 8','-ini:Engine:[DevOptions.Shaders]:ShaderCompilerCoreCountThreshold=0','-ini:Engine:[DevOptions.Shaders]:PercentageUnusedShaderCompilingThreads=85')}else{@()}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$exteriorRoot/$Script" -unattended -nosplash -nosound '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' $exteriorRhi @exteriorAuthoringArgs "-abslog=$exteriorRoot/$Run.log" *> "$exteriorRoot/$Run-console.log"
    $exteriorExit=$LASTEXITCODE
    @{exit_code=$exteriorExit;script=$Script;game_run=$false;interactive_editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$exteriorRoot/$Run.json" -Encoding utf8
    if($exteriorExit -ne 0){throw "Exterior production failed: $exteriorRoot/$Run.log"}
    Write-Output "Exterior production completed: $Script"
} finally {
    if($exteriorHeld){$exteriorGate.ReleaseMutex()}
    $exteriorGate.Dispose()
}
