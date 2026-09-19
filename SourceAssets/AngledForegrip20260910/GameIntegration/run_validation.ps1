param([string]$Run=('final-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
if($Run -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Use a simple run label'}
$fgRoot='D:/FPS3D/FPSGAME'
# Runtime asset review does not require another platform SDK discovery pass.
$env:UE_SKIP_UBT_SDK_SETUP='1'
$fgArgs='"{0}/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=1000 -ResY=700 -unattended -nosplash -ForegripAudit -ForegripRun={1} -ColdSteelProfile=ForegripAudit_{1} -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60" -abslog="{2}/runtime-{1}.log"' -f $fgRoot,$Run,$PSScriptRoot
$fgProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $fgArgs -WindowStyle Hidden -PassThru
Write-Output "Foregrip audit PID $($fgProcess.Id)"
$fgDeadline=[DateTime]::UtcNow.AddSeconds(240)
while(!$fgProcess.WaitForExit(1000)){if([DateTime]::UtcNow -gt $fgDeadline){throw "Foregrip audit timeout PID $($fgProcess.Id)"}}
$fgLog=Get-Content -LiteralPath "$PSScriptRoot/runtime-$Run.log" -Raw
if($fgProcess.ExitCode -ne 0 -or $fgLog -notmatch 'FOREGRIP_AUDIT: COMPLETE failures=0' -or $fgLog -match 'FOREGRIP_AUDIT: FAIL'){throw 'Foregrip runtime regression failed'}
Write-Output "FOREGRIP_RUNTIME_PASS $Run"
