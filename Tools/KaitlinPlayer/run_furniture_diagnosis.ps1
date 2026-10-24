param([string]$Receipt='pipeline-before')
$ErrorActionPreference='Stop'
$furnitureProject='D:/FPS3D/FPSGAME'
$furnitureWork=Join-Path $furnitureProject 'SourceAssets/KaitlinFurniture20261024'
$furnitureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$furnitureHeld=$false
try {
    try {$furnitureHeld=$furnitureGate.WaitOne()} catch [Threading.AbandonedMutexException] {$furnitureHeld=$true}
    $furnitureLog=Join-Path $furnitureWork ($Receipt+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $furnitureProject 'FPSGAME.uproject') '-run=FurnitureBodyDiagnosis' ('-Out='+(Join-Path $furnitureWork ($Receipt+'.json'))) '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$furnitureLog) *> ($furnitureLog+'.stdout.txt')
    $furnitureExit=$LASTEXITCODE
    Get-Content -LiteralPath ($furnitureLog+'.stdout.txt') -Tail 5
    exit $furnitureExit
} finally {
    if($furnitureHeld){$furnitureGate.ReleaseMutex()}
    $furnitureGate.Dispose()
}
