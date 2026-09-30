param([string]$Label='SVDFirstReloadBefore01',[switch]$FromADS,[switch]$ColdEquip,[switch]$Realtime)
$ErrorActionPreference='Stop'
if($Label -notmatch '^SVDFirstReload[a-zA-Z0-9_-]+$'){throw 'Use a fresh SVDFirstReload label'}
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut=Join-Path $taskRoot ('Saved/SVDFirstReload/ColdSteel_'+$Label)
if(Test-Path -LiteralPath $taskOut){throw 'Capture label already exists'}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    Write-Output 'Waiting for the existing UE batch gate'
    $taskHeld=$taskGate.WaitOne(300000)
    if(!$taskHeld){throw 'UE batch busy; no capture started'}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'"){throw 'UE process appeared while waiting; no second process started'}
    New-Item -ItemType Directory -Path $taskOut | Out-Null
    $taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),'/Game/GameMaps/DayNight_Lighting',
        '-game','-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-unattended','-nosplash','-SkipStartupMenu',
        '-SVDFirstReloadAudit',('-ColdSteelProfile='+$Label),
        ('-abslog="'+$taskOut+'/runtime.log"'))
    if(!$Realtime){$taskArgs+=@('-UseFixedTimeStep','-FPS=60')}
    if($FromADS){$taskArgs+='-SVDFirstReloadFromADS'}
    if($ColdEquip){$taskArgs+='-SVDFirstReloadColdEquip'}
    $taskProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
    Write-Output ('SVD capture process '+$taskProcess.Id+'; isolated profile '+$Label)
    if(!$taskProcess.WaitForExit(240000)){
        Stop-Process -Id $taskProcess.Id
        throw 'Owned SVD capture timed out; its isolated game process stopped'
    }
    $taskLog=Get-Content -LiteralPath (Join-Path $taskOut 'runtime.log') -Raw
    if($taskLog -notmatch 'SVD_FIRST_RELOAD capture_complete=1 frames=\d+'){
        throw ('SVD capture did not complete both reloads; '+$taskOut)
    }
    Write-Output ('SVD capture completed both reloads; '+$taskOut)
    exit 0
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
