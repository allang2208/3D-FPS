param(
    [switch]$LaunchAfterExplicitAuthorization,
    [ValidateRange(1025,65533)][int]$Port=17977,
    [string]$ReuseRunRoot
)
$ErrorActionPreference='Stop'
if(-not $LaunchAfterExplicitAuthorization){throw 'Not launched. This script requires separate explicit authorization to start a listen host and one client in two game windows.'}
$projectRoot='D:\FPS3D\FPSGAME'
$base=[IO.Path]::GetFullPath((Join-Path $projectRoot 'SourceAssets\PlantingMultiplayer20261022'))
foreach($target in @('editor','game')){
    $state=Get-Content -LiteralPath (Join-Path $base ('build-'+$target+'-status.json')) -Raw|ConvertFrom-Json
    if($state.state -ne 'succeeded'){throw 'Final Editor and Game builds must succeed before launching the test session.'}
}
if($ReuseRunRoot){
    $runRoot=[IO.Path]::GetFullPath($ReuseRunRoot)
    if(-not $runRoot.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase)-or -not (Test-Path -LiteralPath (Join-Path $runRoot 'launch.json'))){throw 'Only an existing run created by this script can be reused.'}
    $previous=Get-Content -LiteralPath (Join-Path $runRoot 'launch.json') -Raw|ConvertFrom-Json
    foreach($record in $previous.processes){if(Get-Process -Id $record.pid -ErrorAction SilentlyContinue){throw 'A recorded test process is still running; no duplicate session launched.'}}
}else{
    $runRoot=Join-Path $base ('ManualRun-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $runRoot -ErrorAction Stop|Out-Null
}
$engine='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64'
$project='"'+(Join-Path $projectRoot 'FPSGAME.uproject')+'"'
$roles=@('Host','ClientA')
$launches=@()
foreach($role in $roles){
    $userRoot=Join-Path $runRoot $role
    New-Item -ItemType Directory -Path $userRoot -Force|Out-Null
    $testProfileName='PlantingMP_'+$role
    $common=@($project,('-ColdSteelProfile='+$testProfileName),('-UserDir="'+$userRoot+'"'),('-abslog="'+(Join-Path $userRoot 'engine.log')+'"'),'-nosplash','-nop4')
    if($role -eq 'Host'){
        $exe=Join-Path $engine 'UnrealEditor.exe'
        $launchArguments=@($common[0],'/Game/GameMaps/DayNight_Lighting?listen','-game','-windowed','-ResX=1280','-ResY=720',('-port='+$Port))+@($common|Select-Object -Skip 1)
        $job=Start-Process -FilePath $exe -ArgumentList $launchArguments -WindowStyle Normal -PassThru
    }else{
        $exe=Join-Path $engine 'UnrealEditor.exe'
        $launchArguments=@($common[0],('127.0.0.1:'+$Port),'-game','-windowed','-ResX=1280','-ResY=720')+@($common|Select-Object -Skip 1)
        $job=Start-Process -FilePath $exe -ArgumentList $launchArguments -WindowStyle Normal -PassThru
    }
    $launches+=@{role=$role;pid=$job.Id;executable=$exe;arguments=$launchArguments;userRoot=$userRoot;profile=$testProfileName}
    [IO.File]::WriteAllText((Join-Path $runRoot 'launch.json'),(@{runRoot=$runRoot;port=$Port;processes=$launches;automated_assertions=$false}|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
}
[IO.File]::WriteAllText((Join-Path $runRoot 'launch.json'),(@{runRoot=$runRoot;port=$Port;processes=$launches;automated_assertions=$false}|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Write-Output ('Manual network session started; no automated assertions. Data: '+$runRoot)
Write-Output 'Clients may need to reconnect after the server finishes loading. Close only these recorded test processes when finished.'
