param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$RunId,
    [ValidateSet(30,60,120)][int]$Hz=60,
    [switch]$Render=$true,
    [string]$ProjectRoot=''
)
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if($ProjectRoot){$taskRoot=[IO.Path]::GetFullPath($ProjectRoot)}
$taskOut=Join-Path $taskRoot ('Saved/StairMovement/'+$RunId)
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskLog=Join-Path $taskOut 'runtime.log'
if(Test-Path -LiteralPath $taskLog){throw "Run already exists: $taskLog"}
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),'/Game/GameMaps/DayNight_Lighting','-game',
    '-unattended','-nosplash','-nosound','-StairMovementAudit',('-StairRun='+$RunId),
    ('-ColdSteelProfile=StairMovement_'+$RunId),'-UseFixedTimeStep',('-FPS='+$Hz),('-abslog="'+$taskLog+'"'))
if($Render){$taskArgs+=@('-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-ExecCmds="DisableAllScreenMessages,r.MotionBlurQuality 0"')}
else{$taskArgs+='-nullrhi'}
$taskProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
Write-Output "Stairs $Hz Hz PID=$($taskProcess.Id) log=$taskLog"
$taskDeadline=(Get-Date).AddMinutes(5)
while(!$taskProcess.WaitForExit(1000)){
    if((Get-Date) -gt $taskDeadline){$taskProcess.Kill();throw "Owned audit timed out: $taskLog"}
}
$taskText=Get-Content -LiteralPath $taskLog -Raw
$taskPass=$taskText -match 'STAIR_RESULT cases=14 checks=\d+ failures=0' -and $taskProcess.ExitCode -eq 0
$taskResult=[ordered]@{run=$RunId;simulation_hz=$Hz;rendered=[bool]$Render;pass=$taskPass;exit_code=$taskProcess.ExitCode;log=$taskLog}
$taskResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOut 'result.json') -Encoding utf8
$taskResult | ConvertTo-Json
if(!$taskPass){exit 1}
exit 0
