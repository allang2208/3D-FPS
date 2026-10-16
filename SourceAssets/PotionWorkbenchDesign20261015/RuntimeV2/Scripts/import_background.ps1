$ErrorActionPreference='Stop'
$alchemyRoot=Split-Path -Parent $PSScriptRoot
$alchemyHost=Join-Path (Split-Path -Parent $alchemyRoot) 'IntegrationV1/UEImportHost/PotionWorkbenchImport.uproject'
$alchemyOldSkip=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $alchemyHost '-run=pythonscript' "-script=$PSScriptRoot\import_runtime.py" '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' '-LiveCoding=false' "-abslog=$alchemyRoot\Receipts\import-runtime.log" *> (Join-Path $alchemyRoot 'Receipts/import-runtime-stdout.log')
    $alchemyCode=$LASTEXITCODE
    Write-Output "ALCHEMY_IMPORT_EXIT=$alchemyCode"
    exit $alchemyCode
} finally {$env:UE_SKIP_UBT_SDK_SETUP=$alchemyOldSkip}
