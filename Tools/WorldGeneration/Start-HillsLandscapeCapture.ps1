# User-requested visual review. Runtime inputs are shared read-only; saves and
# the native module are copied into a unique host. Never recursively delete it.
param([string]$InputPath='',[string]$SourceSave='',[string]$ModulePath='',[switch]$DaylightAdapter,[Nullable[int]]$WorldSeed,[switch]$RouteWalk,[switch]$CpuTrace,[switch]$FeederPhotos,[switch]$ShoreWalk,[switch]$QuarryWalk,[switch]$QuarryUpperRoad,[string]$RunRoot='',[ValidateRange(1,131072)][int]$TexturePoolMB,[ValidateRange(1,12)][int]$InnerTracePasses)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if(!$RunRoot){$RunRoot=Join-Path $project 'Saved/HillsLandscapeCapture20261117'}
$run=Join-Path $RunRoot (Get-Date -Format 'yyyyMMdd-HHmmss')
$hostPath=Join-Path $run 'Host'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    New-Item -ItemType Directory -Path "$hostPath/Binaries/Win64","$run/Saved/SaveGames","$run/Intermediate","$run/Evidence" -Force | Out-Null
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostPath/FPSGAME.uproject"
    Copy-Item -LiteralPath "$project/Config" -Destination "$hostPath/Config" -Recurse
    foreach($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin') {
        $cache=Join-Path $project "Intermediate/$name"
        if(Test-Path -LiteralPath $cache){Copy-Item -LiteralPath $cache -Destination "$run/Intermediate/$name" -Recurse}
    }
    foreach($folder in 'Content','Plugins','Shaders') {
        New-Item -ItemType Junction -Path (Join-Path $hostPath $folder) -Target (Join-Path $project $folder) | Out-Null
    }
    foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules') {
        $moduleSource="$project/Binaries/Win64/$file"
        if($ModulePath){$moduleSource=Join-Path (Split-Path (Resolve-Path -LiteralPath $ModulePath).Path) $file}
        Copy-Item -LiteralPath $moduleSource -Destination "$hostPath/Binaries/Win64/$file"
    }
    $save=if($SourceSave){(Resolve-Path -LiteralPath $SourceSave).Path}else{"$project/Saved/SaveGames/TemperateHills_World.sav"}
    $saveHash=(Get-FileHash -LiteralPath $save -Algorithm SHA256).Hash
    Copy-Item -LiteralPath $save -Destination "$run/Saved/SaveGames/TemperateHills_World.sav"
    $settings="$project/Saved/Config/WindowsEditor/GameUserSettings.ini"
    if(Test-Path -LiteralPath $settings) {
        New-Item -ItemType Directory -Path "$run/Saved/Config/WindowsEditor" -Force | Out-Null
        Copy-Item -LiteralPath $settings -Destination "$run/Saved/Config/WindowsEditor/GameUserSettings.ini"
    }
    $commands='t.MaxFPS 45,pcg.FrameTime 6,fps.Test.HillsLandscapeCapture'
    $loadingMode='-GameLoadingMode=Complete'
    if($RouteWalk){
        $commands='r.VSync 0,t.MaxFPS 0,pcg.FrameTime 6,fps.Test.HillsRouteWalk'
        $loadingMode='-GameLoadingMode=Quick'
    }
    if($ShoreWalk){
        $commands='r.VSync 0,t.MaxFPS 0,pcg.FrameTime 6,fps.Test.HillsShoreWalk'
        $loadingMode='-GameLoadingMode=Quick'
    }
    if($QuarryWalk){
        $commands='r.VSync 0,t.MaxFPS 0,pcg.FrameTime 6,fps.Test.HillsQuarryWalk'
        $loadingMode='-GameLoadingMode=Quick'
    }
    if($TexturePoolMB){$commands="r.Streaming.PoolSize $TexturePoolMB,"+$commands}
    if($DaylightAdapter){$commands+=',py '+$project+'/Tools/WorldGeneration/hills_capture_daylight.py'}
    $map='/Game/GameMaps/L_TemperateHills_Initial'
    if($null -eq $WorldSeed){$map+='?HillsContinue'}
    $captureArgs=@(
        ('"'+"$hostPath/FPSGAME.uproject"+'"'),$map,
        '-game','-RenderOffscreen','-windowed','-ResX=1920','-ResY=1080','-ForceRes','-unattended','-nosound','-nosplash',
        '-ClearwaterNoMenu','-SkipStartupMenu',$loadingMode,'-HillsLandscapeCapture','-ColdSteelProfile=HillsLandscapeCapture',
        '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
        ('-UserDir="'+$run+'"'),('-abslog="'+"$run/runtime.log"+'"'),
        ('-HillsLandscapeOutput="'+"$run/Evidence"+'"'),
        ('-ExecCmds="'+$commands+'"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False'
    )
    if($RouteWalk){$captureArgs+='-HillsRouteWalk'}
    if($ShoreWalk){$captureArgs+='-HillsShoreWalk'}
    if($QuarryWalk){$captureArgs+='-HillsQuarryWalk'}
    if($QuarryWalk -and $QuarryUpperRoad){$captureArgs+='-QuarryUpperRoad'}
    if($InnerTracePasses){
        if(!$ShoreWalk -or !$CpuTrace){throw 'InnerTracePasses requires ShoreWalk and CpuTrace.'}
        $captureArgs+="-HillsShoreInnerPasses=$InnerTracePasses"
    }
    if($FeederPhotos){$captureArgs+='-HillsFeederPhotos'}
    if($CpuTrace){
        $channels=if($InnerTracePasses){'cpu,gpu,frame,bookmark,log,task,loadtime'}else{'cpu,frame,bookmark,log'}
        $captureArgs+=@("-trace=$channels",'-statnamedevents',('-tracefile="'+$run+'/Evidence/route.utrace"'))
    }
    if($InputPath){$captureArgs+=('-HillsLandscapeInput="'+(Resolve-Path -LiteralPath $InputPath).Path+'"')}
    if($null -ne $WorldSeed){$captureArgs+=@("-HillsSeed=$WorldSeed",'-HillsGen=3')}
    $sdkBefore=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $captureProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $captureArgs -WindowStyle Hidden -PassThru
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$sdkBefore}
    @{pid=$captureProcess.Id;run=$run;source_save=$save;source_save_sha256=$saveHash;
        module_sha256=(Get-FileHash -LiteralPath "$hostPath/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;args=$captureArgs} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$run/launch.json" -Encoding utf8
    Write-Output "HILLS_LANDSCAPE_PID=$($captureProcess.Id)"
    Write-Output "HILLS_LANDSCAPE_RUN=$run"
    $captureProcess.WaitForExit()
    @{exit_code=$captureProcess.ExitCode;source_save_unchanged=((Get-FileHash -LiteralPath $save -Algorithm SHA256).Hash -eq $saveHash);
        finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$run/exit.json" -Encoding utf8
    Write-Output "HILLS_LANDSCAPE_EXIT=$($captureProcess.ExitCode)"
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
