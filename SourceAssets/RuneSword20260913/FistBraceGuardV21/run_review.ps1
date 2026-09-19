$fistReviewPriorSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $fistReviewArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-ExecutePythonScript=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/FistBraceGuardV21/review_in_ue.py','-RenderOffscreen','-unattended','-nosplash','-nosound','-abslog=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/FistBraceGuardV21/ue_review.log')
    $fistReviewProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $fistReviewArgs -WindowStyle Hidden -PassThru
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$fistReviewPriorSdk
}
$fistReviewProcess.Id | Set-Content (Join-Path $PSScriptRoot 'ue_review_pid.txt')
$fistReviewProcess.WaitForExit()
exit $fistReviewProcess.ExitCode
