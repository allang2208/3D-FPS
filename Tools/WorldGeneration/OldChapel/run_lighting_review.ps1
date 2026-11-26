param([int]$Seed=122,[string]$Batch='20261115',[string]$Attempt='before',[switch]$ResumePrepared)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$root=Join-Path $project ('Saved/ChapelRoadReview'+$Batch)
$run=Join-Path $root ($Seed.ToString()+'-'+$Attempt)
$hostPath=Join-Path $run 'Host'
if($ResumePrepared){
    if((Test-Path -LiteralPath "$run/launch.json") -or -not (Test-Path -LiteralPath "$hostPath/Binaries/Win64/UnrealEditor-FPSGAME.dll")){
        throw 'Only a fully prepared, never-launched run may resume after queue timeout'
    }
}else{
if(Test-Path -LiteralPath $run){throw "Review run already exists: $run"}
New-Item -ItemType Directory -Path "$hostPath/Binaries/Win64","$run/Saved/SaveGames","$run/Evidence" -Force | Out-Null
Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostPath/FPSGAME.uproject"
Copy-Item -LiteralPath "$project/Config" -Destination "$hostPath/Config" -Recurse
foreach($folder in 'Content','Plugins','Shaders'){
    if(Test-Path -LiteralPath "$project/$folder"){
        New-Item -ItemType Junction -Path "$hostPath/$folder" -Target "$project/$folder" | Out-Null
    }
}
New-Item -ItemType Directory -Path "$run/Intermediate" -Force | Out-Null
foreach($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){
    if(Test-Path -LiteralPath "$project/Intermediate/$name"){
        Copy-Item -LiteralPath "$project/Intermediate/$name" -Destination "$run/Intermediate/$name" -Recurse
    }
}
foreach($name in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){
    Copy-Item -LiteralPath "$project/Binaries/Win64/$name" -Destination "$hostPath/Binaries/Win64/$name"
}
}
$arguments=@(
    ('"'+$hostPath+'/FPSGAME.uproject"'),'/Game/GameMaps/L_TemperateHills_Initial',
    '-game','-RenderOffscreen','-windowed','-ResX=1280','-ResY=800','-unattended','-nosound','-nosplash',
    '-ClearwaterNoMenu','-SkipStartupMenu','-ChapelLightingReview','-HillsNewWorld',('-HillsSeed='+$Seed),
    '-ColdSteelProfile=ChapelRoadReview','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
    '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
    ('-UserDir="'+$run+'"'),('-abslog="'+$run+'/runtime.log"'),
    ('-ChapelLightingOutput="'+$run+'/Evidence"'),
    '-ExecCmds="t.MaxFPS 45,fps.Test.ChapelLighting"',
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False'
)
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    $held=$gate.WaitOne([TimeSpan]::FromMinutes(20));if(-not $held){throw 'Shared runtime queue timeout'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $job=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    @{pid=$job.Id;seed=$Seed;run=$run;args=$arguments;module_sha256=(Get-FileHash -LiteralPath "$hostPath/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$run/launch.json" -Encoding utf8
    Write-Output "VILLAGE_RUNTIME_PID=$($job.Id) RUN=$run"
    $shutdownStalled=$false
    while(-not $job.WaitForExit(1000)){
        $resultFile=Get-Item -LiteralPath "$run/Evidence/result.json" -ErrorAction SilentlyContinue
        if($resultFile -and ((Get-Date)-$resultFile.LastWriteTime).TotalSeconds -gt 120){
            $state=Get-CimInstance Win32_Process -Filter ("ProcessId="+$job.Id)
            if($state -and $state.HandleCount -eq 0 -and $state.ThreadCount -le 1){
                # The observed renderer shutdown crash can leave a kernel process
                # record after all application handles have closed. Preserve it;
                # do not hold the shared gate indefinitely for completed checks.
                $shutdownStalled=$true
                break
            }
        }
    }
    $code=if($shutdownStalled){$null}else{$job.ExitCode}
    @{exit_code=$code;shutdown_stalled_after_result=$shutdownStalled} | ConvertTo-Json | Set-Content -LiteralPath "$run/exit.json" -Encoding utf8
    Write-Output "VILLAGE_RUNTIME_EXIT=$code SHUTDOWN_STALLED=$shutdownStalled"
    if(Test-Path -LiteralPath "$run/Evidence/result.json"){
        $result=Get-Content -LiteralPath "$run/Evidence/result.json" -Raw | ConvertFrom-Json
        @{captured=$result.capture_completed;seed=$Seed;rooms=$result.interior_vision_rooms;rect_lights=$result.chapel_rect_lights} | ConvertTo-Json -Compress
    }else{throw "Missing completion receipt: $run/runtime.log"}
}finally{
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
