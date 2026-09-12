param(
    [ValidateSet('Rules','Surface','Course','Village','Air','Boundary')][string]$Mode='Village',
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$RunId,
    [ValidateSet(30,60,120)][int]$Hz=60
)
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskOut=Join-Path $taskRoot 'Saved/TraversalTapVillage20260911'
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskLog=Join-Path $taskOut ($RunId+'.log')
if(Test-Path -LiteralPath $taskLog){throw "Run already exists: $taskLog"}
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),'-unattended','-nosplash',('-abslog="'+$taskLog+'"'))
if($Mode -eq 'Rules'){
    $taskArgs+=@('-run=FPSTraversalRulesAudit','-nullrhi','-nosound')
    $taskExpected='TRAVERSAL_WORLD_RESULT checks=\d+ failures=0'
}else{
    $taskMap=if($Mode -eq 'Village'){'/Game/GameMaps/L_Normandy_FPS_Test'}else{'/Game/GameMaps/DayNight_Lighting'}
    $taskArgs+=@($taskMap,'-game','-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-UseFixedTimeStep',('-FPS='+$Hz),'-ExecCmds="DisableAllScreenMessages,r.MotionBlurQuality 0"')
    $taskArgs+=@('-TraversalRuntimeAudit',('-Traversal'+$Mode+'Audit'),('-ColdSteelProfile=TraversalRuntimeAudit_'+$RunId))
    $taskExpected=if($Mode -eq 'Village'){'TRAVERSAL_VILLAGE_RESULT cases=[1-9]\d* failures=0'}elseif($Mode -eq 'Air'){'TRAVERSAL_AIR_RESULT cases=[1-9]\d* failures=0'}elseif($Mode -eq 'Boundary'){'TRAVERSAL_BOUNDARY_RESULT cases=[1-9]\d* failures=0'}else{'TRAVERSAL_RUNTIME_RESULT cases=[1-9]\d* failures=0'}
}
$taskProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
Write-Output "Traversal $Mode PID=$($taskProcess.Id) log=$taskLog"
$taskDeadline=(Get-Date).AddMinutes(5)
while(!$taskProcess.WaitForExit(1000)){
    if((Get-Date) -gt $taskDeadline){$taskProcess.Kill();throw "Owned audit timed out: $taskLog"}
}
$taskText=Get-Content -LiteralPath $taskLog -Raw
$taskPass=($taskText -match $taskExpected) -and ($taskText -notmatch 'TRAVERSAL_(RULE|WORLD|RUNTIME|VILLAGE|AIR|BOUNDARY) FAIL')
$taskResult=[ordered]@{mode=$Mode;run=$RunId;assertions_pass=$taskPass;exit_code=$taskProcess.ExitCode;log=$taskLog;simulation_hz=$Hz}
$taskResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOut ($RunId+'.json')) -Encoding utf8
$taskResult | ConvertTo-Json
if(!$taskPass -or $taskProcess.ExitCode -ne 0){exit 1}
exit 0
