param([Parameter(Mandatory=$true)][string]$Stage)
$ErrorActionPreference='Stop'
$work='D:/FPS3D/FPSGAME/SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
$env:UE_SKIP_UBT_SDK_SETUP='1'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$work/Host/SmithBody.uproject" -run=pythonscript "-script=$PSScriptRoot/$Stage.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$work/$Stage.log" *> "$work/$Stage.console.log"
exit $LASTEXITCODE
