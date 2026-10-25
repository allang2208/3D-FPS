param([ValidateSet('motion','palms')][string]$Stage='motion')
$ErrorActionPreference='Stop'
$furnitureProject='D:/FPS3D/FPSGAME'
$furnitureOut="$furnitureProject/SourceAssets/FurnitureRest20261022/ApartmentLegTransfer20261024R2"
$furnitureScript=if($Stage -eq 'motion'){'save_apartment_leg_transfer.py'}else{'save_leg_transfer_native_support.py'}
$furnitureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$furnitureHeld=$false
try {
    $furnitureHeld=$furnitureGate.WaitOne([TimeSpan]::FromMinutes(20))
    if(-not $furnitureHeld){throw 'UE authoring queue timed out; no assets were changed.'}
    $furnitureEditors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match 'FPSGAME'})
    if($furnitureEditors.Count){throw 'An FPSGAME editor or commandlet is active. Preserve it and use the serialized editor bridge when appropriate.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$furnitureProject/FPSGAME.uproject" -run=pythonscript "-script=$furnitureProject/Tools/FurnitureRest/$furnitureScript" -unattended -nop4 -nosplash -nullrhi "-abslog=$furnitureOut/save-$Stage.log" *> "$furnitureOut/save-$Stage-console.log"
    if($LASTEXITCODE -ne 0){throw "Native animation authoring failed: $LASTEXITCODE; see save-$Stage.log"}
    Write-Output "LEG_TRANSFER_BACKGROUND_SAVED $Stage"
} finally {
    if($furnitureHeld){$furnitureGate.ReleaseMutex()}
    $furnitureGate.Dispose()
}
