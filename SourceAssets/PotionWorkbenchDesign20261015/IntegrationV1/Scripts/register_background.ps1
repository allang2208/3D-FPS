$ErrorActionPreference='Stop'
$potionRoot=Split-Path -Parent $PSScriptRoot
$potionProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$potionMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$potionHeld=$false
$potionPreviousSdkSkip=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$potionHeld=$potionMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$potionHeld=$true}
    if(-not $potionHeld){throw 'UE asset mutex unavailable; no registration submitted.'}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Editor is running; use the current editor bridge instead.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $potionProject '-run=pythonscript' "-script=$PSScriptRoot\install_and_register.py" '-PotionWorkbenchRegister' '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' '-LiveCoding=false' "-abslog=$potionRoot\Receipts\registration-commandlet.log" *> (Join-Path $potionRoot 'Receipts\registration-commandlet-stdout.log')
    $potionExit=$LASTEXITCODE
    Write-Output "POTION_REGISTRATION_EXIT=$potionExit"
    exit $potionExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$potionPreviousSdkSkip
    if($potionHeld){$potionMutex.ReleaseMutex()}
    $potionMutex.Dispose()
}
