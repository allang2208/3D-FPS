param([string]$Run='rebuilt_r2b',[switch]$DefaultAssets,[string]$ExtraFlags='')
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$candidateFlag=if($DefaultAssets){''}else{'-DrumGripCandidate'}
$arguments='"{0}/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=1280 -ResY=720 -UseFixedTimeStep -FPS=60 -unattended -nosplash -nosound {2} -DrumGripAudit -DrumGripCaptureRun={1} -ColdSteelProfile=DrumGripAudit_{1} -ExecCmds="DisableAllScreenMessages" -abslog="{0}/SourceAssets/M4DrumGrip20260910/Revision5/runtime-{1}.log"' -f $root,$Run,$candidateFlag
$process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList ($arguments+' '+$ExtraFlags) -WindowStyle Hidden -PassThru
Write-Output "Review PID $($process.Id)"
$deadline=[DateTime]::UtcNow.AddSeconds(300)
while(!$process.WaitForExit(1000)){if([DateTime]::UtcNow -gt $deadline){throw "Review timeout, PID $($process.Id)"}}
$log=Get-Content -LiteralPath "$root/SourceAssets/M4DrumGrip20260910/Revision5/runtime-$Run.log" -Raw
if($process.ExitCode -ne 0 -or $log -notmatch 'DRUM_GRIP: COMPLETE failures=0' -or $log -match 'DRUM_GRIP: FAIL'){throw 'Review runtime validation failed'}
Write-Output "DRUM_GRIP_REVIEW_PASS $Run"
