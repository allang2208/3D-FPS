param([string]$Script='read_inputs.py',[string]$Stage='inputs',[switch]$Render)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$out=Join-Path $project 'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
$run=Join-Path $project 'Saved/VillageBlacksmithArtR2'
$hostPath=Join-Path $run 'Host'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    if(@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count){throw 'Use the existing editor bridge; do not overlap its loaded packages.'}
    New-Item -ItemType Directory -Force -Path "$out/Logs","$hostPath/Binaries/Win64","$run/Intermediate"|Out-Null
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostPath/FPSGAME.uproject"
    if(-not(Test-Path "$hostPath/Config")){Copy-Item -LiteralPath "$project/Config" -Destination "$hostPath/Config" -Recurse}
    foreach($folder in 'Content','Plugins','Shaders'){
        if((Test-Path "$project/$folder") -and -not(Test-Path "$hostPath/$folder")){New-Item -ItemType Junction -Path "$hostPath/$folder" -Target "$project/$folder"|Out-Null}
    }
    foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){
        if(-not(Test-Path "$hostPath/Binaries/Win64/$file")){Copy-Item -LiteralPath "$project/Binaries/Win64/$file" -Destination "$hostPath/Binaries/Win64/$file"}
    }
    foreach($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){
        if((Test-Path "$project/Intermediate/$name") -and -not(Test-Path "$run/Intermediate/$name")){
            Copy-Item -LiteralPath "$project/Intermediate/$name" -Destination "$run/Intermediate/$name" -Recurse
        }
    }
    $arguments=@(('"'+"$hostPath/FPSGAME.uproject"+'"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/'+$Script+'"'),'-unattended','-nop4','-nosplash','-nosound','-Multiprocess',
        '-AssetGatherAll=false',('-UserDir="'+$run+'"'),('-abslog="'+$out+'/Logs/'+$Stage+'-engine.log"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    if($Render){$arguments+=@('-AllowCommandletRendering','-RenderOffscreen','-windowed','-ResX=1600','-ResY=1200')}
    else{$arguments+='-NullRHI'}
    $previous=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/Logs/$Stage-stdout.log" -RedirectStandardError "$out/Logs/$Stage-stderr.log"
        $null=$process.Handle
        while(-not $process.WaitForExit(1000)){}
        $process.Refresh()
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$previous}
    @{exit_code=$process.ExitCode;finished=(Get-Date -Format o);rendered=[bool]$Render;gameplay_started=$false;isolated_binary_snapshot=$true}|
        ConvertTo-Json|Set-Content -LiteralPath "$out/$Stage-process.json" -Encoding utf8
    if($process.ExitCode -ne 0){exit $process.ExitCode}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
