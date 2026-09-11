param([string]$Weapon='akm',[string]$Grip='canted',[string]$Run='grip-migration-v1',[switch]$UI)
$ErrorActionPreference='Stop'
if($Run -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Invalid run label'}
$gripRoot='D:/FPS3D/FPSGAME'
$gripFlag=@{canted='CantedGripAudit';vertical='VerticalGripAudit';prism='PrismGripAudit';angled='ForegripAudit'}[$Grip]
$gripProfile='ForegripAudit_'+$Run
if($UI){$gripFlag='CantedForegripAudit';$gripProfile='CantedForegripAudit_'+$Run}
$gripArgs='"{0}/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -Multiprocess -windowed -RenderOffscreen -ResX=1000 -ResY=700 -unattended -nosplash -{1} -ForegripRun={2} -ColdSteelProfile={3} -ExecCmds="DisableAllScreenMessages,r.MotionBlurQuality 0,t.MaxFPS 60" -abslog="{4}/runtime-{2}.log"' -f $gripRoot,$gripFlag,$Run,$gripProfile,$PSScriptRoot
if($Weapon -eq 'akm'){$gripArgs+=' -AKMAttachmentAudit'}
if($UI -and $Grip -eq 'vertical'){$gripArgs+=' -AuditVerticalGrip'}
$gripProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $gripArgs -WindowStyle Hidden -PassThru
Write-Output "Grip audit PID $($gripProcess.Id)"
$gripDeadline=[DateTime]::UtcNow.AddSeconds(240)
while(!$gripProcess.WaitForExit(1000)){if([DateTime]::UtcNow -gt $gripDeadline){throw "Grip audit timeout PID $($gripProcess.Id)"}}
$gripLog=Get-Content -LiteralPath "$PSScriptRoot/runtime-$Run.log" -Raw
$gripMarker=if($UI){'CANTED_UI_AUDIT COMPLETE checks=\d+ failures=0'}else{'FOREGRIP_AUDIT: COMPLETE failures=0'}
if($gripProcess.ExitCode -ne 0 -or $gripLog -notmatch $gripMarker -or $gripLog -match '(FOREGRIP_AUDIT:|CANTED_UI_AUDIT) FAIL'){throw 'Grip runtime regression failed'}
Write-Output "GRIP_RUNTIME_PASS $Run"
