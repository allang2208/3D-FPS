param([string]$Attempt='01',[switch]$SkipBuild,[string]$InputFile,[string]$ModuleDirectory)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$root=Join-Path $project 'Saved/SmithWindowReview20261117'
$run=Join-Path $root $Attempt;$hostPath=Join-Path $run 'Host'
if(Test-Path -LiteralPath $run){throw "Review already exists: $run"}
New-Item -ItemType Directory -Force -Path "$hostPath/Binaries/Win64","$run/Intermediate","$run/Saved/SaveGames","$run/Evidence"|Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne(600000)}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'Shared review window unavailable'}
    if(@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count){throw 'Preserve existing editor/runtime'}
    if(-not $SkipBuild){& "$project/Tools/Build/Build-Editor.ps1" *> "$run/build.txt"}
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostPath/FPSGAME.uproject"
    Copy-Item -LiteralPath "$project/Config" -Destination "$hostPath/Config" -Recurse
    foreach($folder in 'Content','Plugins','Shaders'){if(Test-Path "$project/$folder"){New-Item -ItemType Junction -Path "$hostPath/$folder" -Target "$project/$folder"|Out-Null}}
    if(-not $ModuleDirectory){$ModuleDirectory=Join-Path $project 'Binaries/Win64'}
    foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$ModuleDirectory/$file" -Destination "$hostPath/Binaries/Win64/$file"}
    foreach($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){if(Test-Path "$project/Intermediate/$name"){Copy-Item -LiteralPath "$project/Intermediate/$name" -Destination "$run/Intermediate/$name" -Recurse}}
    $map=Join-Path $project 'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
    $before=(Get-FileHash -LiteralPath $map).Hash
    $arguments=@(('"'+"$hostPath/FPSGAME.uproject"+'"'),'/Game/GameMaps/L_TemperateHills_Initial','-game','-RenderOffscreen','-windowed','-ResX=1920','-ResY=1080','-unattended','-nosound','-nosplash',
        '-ClearwaterNoMenu','-SkipStartupMenu','-VillageRuntimeReview','-SmithLoftReview','-HillsNewWorld','-HillsSeed=1518277816','-ColdSteelProfile=SmithLoftReview','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',('-UserDir="'+$run+'"'),('-abslog="'+$run+'/runtime.log"'),
        ('-SmithLoftInput="'+$InputFile+'"'),('-SmithLoftOutput="'+$run+'/Evidence"'),'-ExecCmds="t.MaxFPS 45,fps.Test.SmithLoftReview"',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False')
    $prior=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $job=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
        $null=$job.Handle
        @{pid=$job.Id;seed=1518277816;args=$arguments;map_sha256=$before;module_sha256=(Get-FileHash -LiteralPath "$hostPath/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash}|ConvertTo-Json -Depth 4|Set-Content "$run/launch.json" -Encoding utf8
        Write-Output "SMITH_LOFT_REVIEW_PID=$($job.Id) RUN=$run"
        while(-not $job.WaitForExit(1000)){}
        $job.Refresh()
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$prior}
    @{exit_code=$job.ExitCode;map_unchanged=($before -eq (Get-FileHash -LiteralPath $map).Hash)}|ConvertTo-Json|Set-Content "$run/exit.json" -Encoding utf8
    if(Test-Path "$run/Evidence/result.json"){Get-Content "$run/Evidence/result.json" -TotalCount 18}
    else {Get-Content "$run/runtime.log" -Tail 18}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
