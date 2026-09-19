param([string]$Run='final')
$ErrorActionPreference='Stop'
if($Run -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Use a simple run label'}
$akmIconArgs='"D:/FPS3D/FPSGAME/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=1280 -ResY=800 -unattended -nosplash -ColdSteelInventoryAudit -WeaponIconAudit -AKMAttachmentAudit -ColdSteelProfile=WeaponIconAudit_AKMAttachments_{0} -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60" -abslog="{1}/runtime-icons-{0}.log"' -f $Run,$PSScriptRoot
$akmIconProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $akmIconArgs -WindowStyle Hidden -PassThru
if(!$akmIconProcess.WaitForExit(180000)){throw "Icon audit timeout PID $($akmIconProcess.Id)"}
$akmIconLog=Get-Content -LiteralPath "$PSScriptRoot/runtime-icons-$Run.log" -Raw
if($akmIconLog -notmatch 'WeaponIconAudit: COMPLETE checks=22 failures=0'){throw 'AKM icon audit failed'}
Write-Output 'AKM_ICON_AUDIT_PASS'
