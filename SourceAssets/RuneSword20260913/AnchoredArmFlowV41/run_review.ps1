$armReviewPriorSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $armReviewArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-ExecutePythonScript=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/AnchoredArmFlowV41/review_in_ue.py','-RenderOffscreen','-unattended','-nosplash','-nosound','-abslog=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/AnchoredArmFlowV41/ue_review.log')
    $armReviewProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $armReviewArgs -WindowStyle Hidden -PassThru
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$armReviewPriorSdk
}
$armReviewProcess.Id | Set-Content (Join-Path $PSScriptRoot 'ue_review_pid.txt')
$armReviewProcess.WaitForExit()
exit $armReviewProcess.ExitCode
