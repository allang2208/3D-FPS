param([string]$ReceiptName='capture-headless-20261115-a')
$ErrorActionPreference='Stop'
$hairRoot='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1'
$hairGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$hairHeld=$false
try {
    Write-Output 'Waiting for the read-only asset batch.'
    try {$hairHeld=$hairGate.WaitOne()} catch [Threading.AbandonedMutexException] {$hairHeld=$true}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$hairRoot/ReadHost/HelmetHairReadHost.uproject" '/Engine/Maps/Entry' '-run=pythonscript' '-script=D:/FPS3D/FPSGAME/Tools/ModernTacticalSet/helmet_hair_capture.py' '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-Multiprocess' '-NoAssetRegistryCache' '-AssetGatherAll=false' '-asyncskinnedassetcompilation=0' '-asyncstaticmeshcompilation=0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen' "-abslog=$hairRoot/$ReceiptName.log" *> "$hairRoot/$ReceiptName.txt"
    $hairExit=$LASTEXITCODE;Write-Output "Hair capture exit=$hairExit";exit $hairExit
} finally {if($hairHeld){$hairGate.ReleaseMutex()};$hairGate.Dispose()}
