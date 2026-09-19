$chargedArmReviewPriorSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $chargedArmReviewArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-ExecutePythonScript=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/ChargedArmV22/review_in_ue.py','-RenderOffscreen','-unattended','-nosplash','-nosound','-abslog=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/ChargedArmV22/ue_review.log')
    $chargedArmReviewProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $chargedArmReviewArgs -WindowStyle Hidden -PassThru
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$chargedArmReviewPriorSdk
}
$chargedArmReviewProcess.Id | Set-Content (Join-Path $PSScriptRoot 'ue_review_pid.txt')
$chargedArmReviewProcess.WaitForExit()
exit $chargedArmReviewProcess.ExitCode
