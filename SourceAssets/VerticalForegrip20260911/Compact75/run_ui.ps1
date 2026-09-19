$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$compactArgs='"D:/FPS3D/FPSGAME/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=1200 -ResY=800 -unattended -nosplash -VerticalForegripAudit -ColdSteelProfile=VerticalForegripAudit_Compact75_01 -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60" -abslog="{0}/ui_final.log"' -f $PSScriptRoot
$compactProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $compactArgs -WindowStyle Hidden -PassThru
Write-Output "Compact UI audit PID $($compactProcess.Id)"
$compactDeadline=[DateTime]::UtcNow.AddSeconds(180)
while(!$compactProcess.WaitForExit(1000)){if([DateTime]::UtcNow -gt $compactDeadline){throw 'Owned compact UI audit timed out'}}
$compactLog=Get-Content "$PSScriptRoot/ui_final.log" -Raw
if($compactLog -notmatch 'VERTICAL_UI_AUDIT COMPLETE checks=24 failures=0'){throw 'Compact UI audit did not pass'}
foreach($name in @('vertical-side','vertical-rotated','vertical-first-person','vertical-all-parts')){Copy-Item -LiteralPath "D:/FPS3D/FPSGAME/Saved/VerticalForegripAudit/$name.png" -Destination "$PSScriptRoot/$name.png"}
Write-Output 'COMPACT_UI_PASS'
