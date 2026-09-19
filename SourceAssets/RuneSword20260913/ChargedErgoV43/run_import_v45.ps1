# Install the V45 charged-hold clips through a separate ImportHost process.
# The interactive FPSGAME editor must be closed first: it holds the .uasset files open,
# which is what made the earlier standalone V43 run fail with "Animation save failed".
$chargedHoldPreviousSdkSetting = $env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\SourceAssets\RuneSword20260913\WeightLeftV5\ImportHost\RuneSwordImport.uproject' -run=pythonscript '-script=D:\FPS3D\FPSGAME\SourceAssets\RuneSword20260913\ChargedErgoV43\import_revision_v45.py' -unattended -nosplash -NullRHI '-abslog=D:\FPS3D\FPSGAME\SourceAssets\RuneSword20260913\ChargedErgoV43\import_v45.log' *> (Join-Path $PSScriptRoot 'import_console_v45.log')
    $chargedHoldImportExit = $LASTEXITCODE
}
finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $chargedHoldPreviousSdkSetting
}
exit $chargedHoldImportExit
