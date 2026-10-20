param([string]$Label='svch-check-20261018-a1',[switch]$Studio,[switch]$NoCorrectives)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject ('Saved/SVCHPoseAudit/'+$Label)
if(Test-Path -LiteralPath $taskOutput){throw 'Choose a new label; prior evidence is preserved.'}
$runtimeLog=Join-Path $PSScriptRoot ('runtime-'+$Label+'.log')
$env:UE_SKIP_UBT_SDK_SETUP='1'
$arguments=@(
 ('"'+$taskProject+'/FPSGAME.uproject"'),
 '/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
 '-game','-windowed','-RenderOffscreen','-ResX=1280','-ResY=720',
 '-unattended','-nosplash','-nosound','-d3d12','-FixedSeed','-SkipStartupMenu','-DisablePython',
 '-UseFixedTimeStep','-FPS=60','-SVCHPoseAudit','-SVCHReloadOnly',
 ('-ColdSteelProfile=SVCHPoseAudit_'+$Label),('-GunplayLabel='+$Label),
 ('-abslog="'+$runtimeLog+'"'))
if($Studio){$arguments+='-SVCHPoseAuditStudio'}
if($NoCorrectives){$arguments+='-ExecCmds="fps.Arms.JointCorrectives 0"'}
$ownedTest=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
Write-Output "SVCH offscreen runtime process $($ownedTest.Id); isolated profile; $taskOutput"
$ownedTest.WaitForExit()
$completion=Join-Path $taskOutput 'completion.json'
if(!(Test-Path -LiteralPath $completion)){throw "No completion record; inspect $runtimeLog"}
$result=Get-Content -LiteralPath $completion -Raw|ConvertFrom-Json
$result|Add-Member -NotePropertyName process_exit -NotePropertyValue $ownedTest.ExitCode
$result|Add-Member -NotePropertyName runtime_log -NotePropertyValue $runtimeLog
$result|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $taskOutput 'result.json') -Encoding utf8
$result|ConvertTo-Json -Depth 5
if($ownedTest.ExitCode-ne 0 -or !$result.completed){exit 1}
