$groupFlowPreviousSdk = $env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/WeightLeftV5/ImportHost/RuneSwordImport.uproject' -run=pythonscript '-script=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/OffscreenLeftInspectV42/import_upgrade.py' -unattended -nosplash -NullRHI '-abslog=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/OffscreenLeftInspectV42/import.log' *> (Join-Path $PSScriptRoot 'import_console.log')
    $groupFlowImportExit = $LASTEXITCODE
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $groupFlowPreviousSdk
}
exit $groupFlowImportExit
