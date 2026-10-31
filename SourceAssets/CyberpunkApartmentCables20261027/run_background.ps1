param([string]$Script='production_all.py',[string]$Run='production-01',[switch]$Render)
$ErrorActionPreference='Stop'
$urbanRoot=$PSScriptRoot
$urbanGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$urbanHeld=$false
try {
    $urbanHeld=$urbanGate.WaitOne([TimeSpan]::FromSeconds(900))
    if(-not $urbanHeld){throw 'UE batch window busy; no background process started.'}
    $urbanProcesses=@(Get-CimInstance Win32_Process)
    if($urbanProcesses | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Preserve active UE / build work; background publication deferred.'}
    $urbanRhi=if($Render){'-AllowCommandletRendering'}else{'-nullrhi'}
    $urbanArgs=if($Render){@('-ExecCmds=Editor.AsyncTextureCompilationMaxConcurrency 1,Editor.AsyncAssetCompilationMaxConcurrency 2,Editor.AsyncAssetCompilationMaxMemoryUsage 8','-ini:Engine:[DevOptions.Shaders]:ShaderCompilerCoreCountThreshold=0','-ini:Engine:[DevOptions.Shaders]:PercentageUnusedShaderCompilingThreads=85')}else{@()}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$urbanRoot/$Script" -unattended -nosplash -nosound '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' $urbanRhi @urbanArgs "-abslog=$urbanRoot/$Run.log" *> "$urbanRoot/$Run-console.log"
    $urbanExit=$LASTEXITCODE
    @{exit_code=$urbanExit;script=$Script;game_run=$false;interactive_editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$urbanRoot/$Run.json" -Encoding utf8
    if($urbanExit -ne 0){throw "Urban production failed: $urbanRoot/$Run.log"}
    Write-Output "Urban production completed: $Script"
}finally{if($urbanHeld){$urbanGate.ReleaseMutex()};$urbanGate.Dispose()}
