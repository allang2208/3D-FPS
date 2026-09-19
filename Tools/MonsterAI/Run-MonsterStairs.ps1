param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$RunId,
    [ValidateSet(30,60,120)][int]$Hz=60,
    [ValidateRange(-1,11)][int]$Case=-1,
    [ValidateRange(-1,2)][int]$Species=-1
)
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskOut=Join-Path $taskRoot ('Saved/MonsterStairs/'+$RunId)
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskLog=Join-Path $taskOut 'runtime.log'
if(Test-Path -LiteralPath $taskLog){throw "Run already exists: $taskLog"}
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),'/Game/Tests/MonsterStairs/L_MonsterStairs','-game',
    '-unattended','-nosplash','-nosound','-MonsterStairAudit',('-MonsterStairRun='+$RunId),
    ('-ColdSteelProfile=MonsterStairs_'+$RunId),'-UseFixedTimeStep',('-FPS='+$Hz),('-abslog="'+$taskLog+'"'),
    '-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-ExecCmds="DisableAllScreenMessages,r.MotionBlurQuality 0"')
if(($Case -ge 0) -ne ($Species -ge 0)){throw 'Specify both Case and Species for a single case'}
$taskExpectedCases=36
if($Case -ge 0){$taskArgs+=@(('-MonsterStairCase='+$Case),('-MonsterStairSpecies='+$Species));$taskExpectedCases=1}
$taskProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
Write-Output "Monster stairs $Hz Hz PID=$($taskProcess.Id) log=$taskLog"
$taskDeadline=(Get-Date).AddMinutes(12)
while(!$taskProcess.WaitForExit(1000)){
    if((Get-Date) -gt $taskDeadline){$taskProcess.Kill();throw "Owned audit timed out: $taskLog"}
}
$taskText=Get-Content -LiteralPath $taskLog -Raw
$taskPass=$taskText -match ('MONSTER_STAIR_RESULT cases='+$taskExpectedCases+' checks=\d+ failures=0') -and $taskProcess.ExitCode -eq 0
$taskResult=[ordered]@{run=$RunId;simulation_hz=$Hz;rendered=$true;pass=$taskPass;exit_code=$taskProcess.ExitCode;log=$taskLog}
$taskResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOut 'result.json') -Encoding utf8
$taskResult | ConvertTo-Json
if(!$taskPass){exit 1}
exit 0
