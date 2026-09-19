param([string]$Run='akm-v1',[switch]$Readback,[switch]$ExistingProfile,[string]$SourceProfile='ColdSteelPlayer',[switch]$SightAudit)
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$flags=if($Readback){'-AKMReadback -nosound'}else{''}
if($SightAudit){$flags+=' -AKMSightAudit'}
if($ExistingProfile){
    $flags+=' -AKMExistingProfile'
    foreach($slot in @('A','B')){foreach($ext in @('sav','sha1')){
        $source="$root/Saved/SaveGames/${SourceProfile}_${slot}.$ext"
        $target="$root/Saved/SaveGames/ColdSteel_AKMIntegrationAudit_${Run}_${slot}.$ext"
        if(Test-Path -LiteralPath $target){throw "Use a fresh audit name; target exists: $target"}
        if(Test-Path -LiteralPath $source){Copy-Item -LiteralPath $source -Destination $target}
    }}
}
$args='"{0}/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=960 -ResY=540 -AudioMixer -ini:Engine:[Audio]:UnfocusedVolumeMultiplier=1.0 -unattended -nosplash -AKMIntegrationAudit -AKMRun={1} -ColdSteelProfile=AKMIntegrationAudit_{1} {2} -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60,au.NeverDisableSubmixes 1" -abslog="{0}/SourceAssets/AKMIntegration20260910/runtime-{1}{3}.log"' -f $root,$Run,$flags,($(if($Readback){'-readback'}else{''}))
$p=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
Write-Output "AKM audit PID $($p.Id)"
if(!$p.WaitForExit(180000)){throw "AKM audit timeout PID $($p.Id)"}
$log=Get-Content "$PSScriptRoot/runtime-$Run$(if($Readback){'-readback'}).log" -Raw
if($p.ExitCode -ne 0 -or $log -notmatch 'AKM_INTEGRATION: COMPLETE failures=0' -or $log -match 'AKM_INTEGRATION: FAIL'){throw 'AKM audit failed'}
Write-Output 'AKM_INTEGRATION_PASS'
