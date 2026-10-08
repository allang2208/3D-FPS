$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME'
$bcExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$bcOut="$bcProject/SourceAssets/BoundCongregateMeshy20261006/MeleeV17/Review"
function Require-BCReviewIdle {
    $bcActive=Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor|^FPSGAME|^UnrealBuildTool' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }
    if($bcActive){throw 'Preserve the active UE process; resume this requested review after it finishes.'}
}
Require-BCReviewIdle
& $bcExe "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/review_ue_melee_v17.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$bcOut/compressed-review.log" *> "$bcOut/compressed-review-console.log"
if($LASTEXITCODE -ne 0){throw 'Compressed pose review failed; see its log.'}
Require-BCReviewIdle
& $bcExe "$bcProject/FPSGAME.uproject" -run=BoundCongregateRigReview -MeleeV17 -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$bcOut/native-proxy-review.log" *> "$bcOut/native-proxy-review-console.log"
if($LASTEXITCODE -ne 0){throw 'Native proxy review failed; see its log.'}
Write-Output 'REQUESTED_MELEE_V17_REVIEWS_COMPLETED'
