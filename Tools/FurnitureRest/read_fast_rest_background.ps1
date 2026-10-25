$ErrorActionPreference='Stop'
$furnitureProject='D:/FPS3D/FPSGAME'
$furnitureOut="$furnitureProject/SourceAssets/FurnitureRest20261022/ApartmentFastRest20261024R2"
$furnitureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$furnitureHeld=$false
try {
    $furnitureHeld=$furnitureGate.WaitOne([TimeSpan]::FromMinutes(20))
    if(-not $furnitureHeld){throw 'UE authoring queue timed out.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$furnitureProject/FPSGAME.uproject" -run=pythonscript "-script=$furnitureProject/Tools/FurnitureRest/read_apartment_fast_rest_saved.py" -unattended -nop4 -nosplash -nosound -nullrhi -ddc=NoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache/Authoring/FurnitureRest' "-abslog=$furnitureOut/read-native.log" *> "$furnitureOut/read-native-console.log"
    if($LASTEXITCODE -ne 0){throw "Native animation read failed: $LASTEXITCODE"}
    Write-Output 'FAST_REST_NATIVE_READ_COMPLETE'
} finally {
    if($furnitureHeld){$furnitureGate.ReleaseMutex()}
    $furnitureGate.Dispose()
}
