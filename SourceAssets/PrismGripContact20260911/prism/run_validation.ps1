param([string]$Run=('prism-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
if($Run -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Use a simple run label'}
$gripRoot='D:/FPS3D/FPSGAME'
$gripArgs='"{0}/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=1000 -ResY=700 -unattended -nosplash -PrismGripAudit -ForegripRun={1} -ColdSteelProfile=ForegripAudit_{1} -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60" -abslog="{2}/runtime-{1}.log"' -f $gripRoot,$Run,$PSScriptRoot
$gripProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $gripArgs -WindowStyle Hidden -PassThru
Write-Output "Prism grip audit PID $($gripProcess.Id)"
$gripDeadline=[DateTime]::UtcNow.AddSeconds(240)
while(!$gripProcess.WaitForExit(1000)){if([DateTime]::UtcNow -gt $gripDeadline){throw "Prism grip audit timeout PID $($gripProcess.Id)"}}
$gripLog=Get-Content -LiteralPath "$PSScriptRoot/runtime-$Run.log" -Raw
if($gripProcess.ExitCode -ne 0 -or $gripLog -notmatch 'FOREGRIP_AUDIT: COMPLETE failures=0' -or $gripLog -match 'FOREGRIP_AUDIT: FAIL'){throw 'Prism grip runtime regression failed'}
Write-Output "PRISM_GRIP_RUNTIME_PASS $Run"
