$ErrorActionPreference='Stop'
$furnitureProject='D:/FPS3D/FPSGAME'
$furnitureOut="$furnitureProject/SourceAssets/FurnitureRest20261022/ApartmentFastRest20261024R2"
$furnitureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$furnitureHeld=$false
try {
    $furnitureHeld=$furnitureGate.WaitOne([TimeSpan]::FromMinutes(20))
    if(-not $furnitureHeld){throw 'UE authoring queue timed out; no assets changed.'}
    $furnitureEditors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match 'FPSGAME'})
    if($furnitureEditors | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}){throw 'Another FPSGAME commandlet is active; preserve it.'}
    if($furnitureEditors.Count){
        # This revision writes four new packages only. Existing source packages
        # are read-only; never overwrite a destination the live editor can own.
        $furnitureTargets=Get-Content -LiteralPath "$furnitureOut/background_target_ownership.json" -Raw | ConvertFrom-Json
        foreach($furnitureTarget in $furnitureTargets){
            $furnitureDisk="$furnitureProject/Content/"+$furnitureTarget.path.Substring(6)+'.uasset'
            if($furnitureTarget.loaded -or (Test-Path -LiteralPath $furnitureDisk)){throw 'Destination may be owned by the running editor; use its bridge.'}
        }
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$furnitureProject/FPSGAME.uproject" -run=pythonscript "-script=$furnitureProject/Tools/FurnitureRest/save_apartment_fast_rest.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$furnitureOut/save-native.log" *> "$furnitureOut/save-native-console.log"
    if($LASTEXITCODE -ne 0){throw "Native animation authoring failed: $LASTEXITCODE"}
    Write-Output 'FAST_REST_BACKGROUND_SAVED'
} finally {
    if($furnitureHeld){$furnitureGate.ReleaseMutex()}
    $furnitureGate.Dispose()
}
