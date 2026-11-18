param([string]$Stage='finish-background-01',[switch]$SkipBuild)
$ErrorActionPreference='Stop'
$loftEntry=if($env:SMITH_LOFT_SCRIPT){$env:SMITH_LOFT_SCRIPT}else{'finish.py'}
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$out=Join-Path $project 'SourceAssets/HillsVillageBlacksmith20261117/LoftR3'
$run=Join-Path $project 'Saved/VillageBlacksmithLoftR3'
$hostPath=Join-Path $run 'Host'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne(600000)}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'Shared production batch window unavailable; no engine process started.'}
    if(@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count){throw 'Existing editor preserved; use its bridge.'}
    New-Item -ItemType Directory -Force -Path "$out/Logs","$hostPath/Binaries/Win64","$run/Intermediate"|Out-Null
    if(-not $SkipBuild){
        & "$project/Tools/Build/Build-Editor.ps1" *> "$out/Logs/$Stage-build.txt"
        if(-not $?){throw 'Editor build failed; inspect the stage build log.'}
    }
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostPath/FPSGAME.uproject"
    if(-not(Test-Path "$hostPath/Config")){Copy-Item -LiteralPath "$project/Config" -Destination "$hostPath/Config" -Recurse}
    foreach($folder in 'Content','Plugins','Shaders'){
        if((Test-Path "$project/$folder") -and -not(Test-Path "$hostPath/$folder")){New-Item -ItemType Junction -Path "$hostPath/$folder" -Target "$project/$folder"|Out-Null}
    }
    foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$project/Binaries/Win64/$file" -Destination "$hostPath/Binaries/Win64/$file"}
    foreach($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){
        if((Test-Path "$project/Intermediate/$name") -and -not(Test-Path "$run/Intermediate/$name")){Copy-Item -LiteralPath "$project/Intermediate/$name" -Destination "$run/Intermediate/$name" -Recurse}
    }
    $arguments=@(('"'+"$hostPath/FPSGAME.uproject"+'"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/'+$loftEntry+'"'),'-unattended','-nop4','-nosplash','-nosound','-Multiprocess','-NullRHI',
        '-AssetGatherAll=false',('-UserDir="'+$run+'"'),('-abslog="'+$out+'/Logs/'+$Stage+'-engine.log"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $priorSkip=$env:UE_SKIP_UBT_SDK_SETUP;$priorMode=$env:BLACKSMITH_LOFT_HEADLESS
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1';$env:BLACKSMITH_LOFT_HEADLESS='1'
        $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/Logs/$Stage-stdout.log" -RedirectStandardError "$out/Logs/$Stage-stderr.log"
        $null=$process.Handle
        while(-not $process.WaitForExit(1000)){}
        $process.Refresh()
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$priorSkip;$env:BLACKSMITH_LOFT_HEADLESS=$priorMode}
    @{exit_code=$process.ExitCode;finished=(Get-Date -Format o);rendered=$false;gameplay_started=$false;background_build=(-not $SkipBuild)} | ConvertTo-Json | Set-Content -LiteralPath "$out/$Stage-process.json" -Encoding utf8
    Get-Content -LiteralPath "$out/Logs/$Stage-engine.log" -Tail 20
    if($process.ExitCode -ne 0){exit $process.ExitCode}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
