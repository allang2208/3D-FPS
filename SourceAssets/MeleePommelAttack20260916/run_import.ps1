# Import the fourth combo hit through a separate ImportHost process.
# Use this when the interactive editor is closed; while it is open, run
#   python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/MeleePommelAttack20260916/import_pommel.py
$pommelPreviousSdkSetting = $env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\SourceAssets\RuneSword20260913\WeightLeftV5\ImportHost\RuneSwordImport.uproject' -run=pythonscript '-script=D:\FPS3D\FPSGAME\SourceAssets\MeleePommelAttack20260916\import_pommel.py' -unattended -nosplash -NullRHI '-abslog=D:\FPS3D\FPSGAME\SourceAssets\MeleePommelAttack20260916\import.log' *> (Join-Path $PSScriptRoot 'import_console.log')
    $pommelImportExit = $LASTEXITCODE
}
finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $pommelPreviousSdkSetting
}
exit $pommelImportExit
