$prev = $env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/WeightLeftV5/ImportHost/RuneSwordImport.uproject' -run=pythonscript '-script=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/InspectGripArcV46/import_inspect_v53.py' -unattended -nosplash -NullRHI '-abslog=D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/InspectGripArcV46/import_v53.log' *> 'D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/InspectGripArcV46/import_console_v53.log'
    exit $LASTEXITCODE
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $prev
}