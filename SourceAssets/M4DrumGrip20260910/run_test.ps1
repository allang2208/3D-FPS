param([string]$Run='grip_a')
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$args='"{0}/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=1280 -ResY=720 -unattended -nosplash -nosound -DrumGripCandidate -DrumGripAudit -ColdSteelProfile=DrumGripAudit_{1} -abslog="{0}/SourceAssets/M4DrumGrip20260910/runtime-{1}.log"' -f $root,$Run
$p=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
Write-Output "Drum grip test PID $($p.Id)"
if(!$p.WaitForExit(120000)){throw "Test timed out PID $($p.Id)"}
$log=Get-Content "$root/SourceAssets/M4DrumGrip20260910/runtime-$Run.log" -Raw
if($p.ExitCode -ne 0 -or $log -notmatch 'DRUM_GRIP: COMPLETE failures=0' -or $log -match 'DRUM_GRIP: FAIL'){throw 'Drum grip runtime test failed'}
Write-Output 'DRUM_GRIP_RUNTIME_PASS'
