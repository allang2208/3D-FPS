$priorSdk = $env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $diagArgs = @('D:/FPS3D/FPSGAME/FPSGAME.uproject',
        '-ExecutePythonScript=D:/FPS3D/FPSGAME/SourceAssets/ToolEnhance20260925/ue_render_viewmodel_offscreen.py',
        '-RenderOffscreen', '-unattended', '-nosplash', '-nosound',
        '-abslog=D:/FPS3D/FPSGAME/Saved/Production/tool-enhance-viewmodel-diag-ue.log')
    $diagProcess = Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $diagArgs -WindowStyle Hidden -PassThru
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $priorSdk
}
$diagProcess.Id | Set-Content 'D:/FPS3D/FPSGAME/Saved/Production/tool-enhance-viewmodel-diag-pid.txt'
$diagProcess.WaitForExit()
exit $diagProcess.ExitCode
