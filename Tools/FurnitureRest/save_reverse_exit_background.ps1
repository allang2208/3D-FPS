$ErrorActionPreference='Stop'
$reverseProject='D:/FPS3D/FPSGAME'
$reverseOut="$reverseProject/SourceAssets/FurnitureRest20261022/ApartmentReverseExit20261024"
$reverseGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$reverseHeld=$false
try {
    $reverseHeld=$reverseGate.WaitOne([TimeSpan]::FromMinutes(20))
    if(-not $reverseHeld){throw 'UE authoring queue timed out; no assets changed.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$reverseProject/FPSGAME.uproject" -run=pythonscript "-script=$reverseProject/Tools/FurnitureRest/save_apartment_reverse_exit.py" -unattended -nop4 -nosplash -nosound -nullrhi -AssetGatherAll=false -NoAssetRegistryCache '-AssetRegistryCacheRootFolder=C:/Users/allan/AppData/Local/Temp/ApartmentReverseExit20261024/AssetRegistry' -ddc=NoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache/Authoring/FurnitureRest' "-abslog=$reverseOut/save-native.log" *> "$reverseOut/save-native-console.log"
    $reverseEngineCode=$LASTEXITCODE
    if($reverseEngineCode -ne 0){throw "Commandlet returned $reverseEngineCode; inspect the scoped save/read receipts before resuming."}
    Write-Output 'REVERSE_EXIT_BACKGROUND_SAVED'
} finally {
    if($reverseHeld){$reverseGate.ReleaseMutex()}
    $reverseGate.Dispose()
}
