$ErrorActionPreference='Stop'
$potionRoot=Split-Path -Parent $PSScriptRoot
$potionPreviousSdkSkip=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $potionRoot 'UEImportHost/PotionWorkbenchImport.uproject') '-run=pythonscript' "-script=$PSScriptRoot\import_assets.py" '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' '-LiveCoding=false' "-abslog=$potionRoot\Receipts\ue-import.log" *> (Join-Path $potionRoot 'Receipts\ue-import-stdout.log')
    $potionExit=$LASTEXITCODE
    Write-Output "POTION_IMPORT_EXIT=$potionExit"
    exit $potionExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$potionPreviousSdkSkip
}
