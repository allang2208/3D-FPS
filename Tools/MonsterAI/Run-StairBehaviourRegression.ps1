param([ValidateSet('AI','Maggot')][string]$Mode='AI',[Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$RunId)
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskOut=Join-Path $taskRoot ('Saved/MonsterStairs/'+$RunId)
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskLog=Join-Path $taskOut 'runtime.log'
if(Test-Path -LiteralPath $taskLog){throw "Run already exists: $taskLog"}
$taskMap=if($Mode -eq 'AI'){'/Game/Tests/MonsterAI/L_MonsterAI'}else{'/Game/Tests/PoisonMaggot/L_PoisonMaggot'}
$taskFlag=if($Mode -eq 'AI'){'-MonsterAIAudit'}else{'-PoisonMaggotAudit'}
$taskMarker=if($Mode -eq 'AI'){'MONSTER_AI_COMPLETE failures=0'}else{'MAGGOT_AUDIT_COMPLETE failures=0'}
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),$taskMap,'-game','-unattended','-nosplash','-nosound',
    $taskFlag,('-ColdSteelProfile=MonsterStairs_'+$RunId),'-UseFixedTimeStep','-FPS=60',('-abslog="'+$taskLog+'"'),
    '-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-ExecCmds="DisableAllScreenMessages,r.MotionBlurQuality 0"')
$taskProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
Write-Output "$Mode regression PID=$($taskProcess.Id) log=$taskLog"
$taskDeadline=(Get-Date).AddMinutes(6)
while(!$taskProcess.WaitForExit(1000)){
    if((Get-Date) -gt $taskDeadline){$taskProcess.Kill();throw "Owned audit timed out: $taskLog"}
}
$taskText=Get-Content -LiteralPath $taskLog -Raw
$taskPass=$taskText -match $taskMarker -and $taskProcess.ExitCode -eq 0
$taskResult=[ordered]@{run=$RunId;mode=$Mode;rendered=$true;pass=$taskPass;exit_code=$taskProcess.ExitCode;log=$taskLog}
$taskResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOut 'result.json') -Encoding utf8
$taskResult | ConvertTo-Json
if(!$taskPass){exit 1}
exit 0
