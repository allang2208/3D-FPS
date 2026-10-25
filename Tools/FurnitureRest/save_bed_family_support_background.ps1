$ErrorActionPreference='Stop'
$bedProject='D:/FPS3D/FPSGAME'
$bedOut="$bedProject/SourceAssets/FurnitureRest20261022/BedFamilyReuse20261025"
$bedGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$bedHeld=$false
try {
    try {$bedHeld=$bedGate.WaitOne([TimeSpan]::FromMinutes(20))}
    catch [Threading.AbandonedMutexException] {
        $bedHeld=$true
        $bedActive=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')})
        if($bedActive.Count){throw 'Abandoned UE operation may still be active; preserve its state.'}
        Write-Output 'No UE process remains after the abandoned lease; continuing the new bed packages only.'
    }
    if(-not $bedHeld){throw 'UE authoring queue timed out; no bed assets changed.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$bedProject/FPSGAME.uproject" -run=pythonscript "-script=$bedProject/Tools/FurnitureRest/save_bed_family_support.py" -unattended -nop4 -nosplash -nosound -nullrhi -AssetGatherAll=false -NoAssetRegistryCache '-AssetRegistryCacheRootFolder=C:/Users/allan/AppData/Local/Temp/BedFamilyReuse20261025/AssetRegistry' -ddc=NoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache/Authoring/FurnitureRest' "-abslog=$bedOut/save-native.log" *> "$bedOut/save-native-console.log"
    if($LASTEXITCODE -ne 0){throw "Commandlet returned $LASTEXITCODE; inspect the scoped save/read receipts before resuming."}
    Write-Output 'BED_FAMILY_BACKGROUND_SAVED'
} finally {
    if($bedHeld){$bedGate.ReleaseMutex()}
    $bedGate.Dispose()
}
