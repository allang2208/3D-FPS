param([string]$Run=('PickupRestoreAudit_'+(Get-Date -Format 'yyyyMMdd_HHmmss')))
$ErrorActionPreference='Stop'
if($Run -notmatch '^PickupRestoreAudit_[a-zA-Z0-9_]+$'){throw 'Use an isolated PickupRestoreAudit_ profile name.'}
$project=Split-Path $PSScriptRoot -Parent
$output=Join-Path $project "Saved/PickupBeginPlayFix/$Run"
New-Item -ItemType Directory -Path $output -Force | Out-Null
$env:UE_SKIP_UBT_SDK_SETUP='1'
foreach($phase in @('seed','restore')){
    $extra=if($phase -eq 'restore'){'-WorldInteractionRestoreAudit'}else{''}
    $log=Join-Path $output "$phase.log"
    $arguments='"{0}/FPSGAME.uproject" /Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation -game -windowed -RenderOffscreen -ResX=1000 -ResY=700 -unattended -nosplash -WorldInteractionAudit {1} -ColdSteelProfile={2} -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60" -abslog="{3}"' -f $project,$extra,$Run,$log
    $process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Write-Output "$phase PID=$($process.Id)"
    $deadline=[DateTime]::UtcNow.AddMinutes(4)
    while(!$process.WaitForExit(1000)){
        if([DateTime]::UtcNow -gt $deadline){throw "$phase timed out; inspect PID $($process.Id) and $log"}
    }
    $result=Get-Content -LiteralPath $log -Raw
    if($process.ExitCode -ne 0 -or $result -notmatch 'WorldInteractionAudit: COMPLETE checks=\d+ failures=0' -or $result -match 'WorldInteractionAudit: FAIL|Fatal error!'){
        throw "$phase failed; inspect $log"
    }
    if($phase -eq 'restore' -and $result -notmatch 'PASS fresh process BeginPlay restores saved M4 and AKM models'){
        throw 'Missing fresh process restore assertion.'
    }
    Write-Output "$phase PASS"
}
