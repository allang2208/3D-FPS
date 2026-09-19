# UE-side read-back of the re-imported pommel clip through the ImportHost project.
# Same channel as run_import.ps1: works while the interactive editor is closed.
$pommelPreviousSdkSetting = $env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\SourceAssets\RuneSword20260913\WeightLeftV5\ImportHost\RuneSwordImport.uproject' -run=pythonscript '-script=D:\FPS3D\FPSGAME\SourceAssets\MeleePommelAttack20260916\readback_ue.py' -unattended -nosplash -NullRHI '-abslog=D:\FPS3D\FPSGAME\SourceAssets\MeleePommelAttack20260916\readback.log' *> (Join-Path $PSScriptRoot 'readback_console.log')
    $pommelReadbackExit = $LASTEXITCODE
}
finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $pommelPreviousSdkSetting
}
exit $pommelReadbackExit
