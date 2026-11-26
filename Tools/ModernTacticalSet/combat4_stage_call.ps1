param([Parameter(Mandatory=$true)][string]$Script,[string]$Label='stage')
$ErrorActionPreference='Stop'
$r4Project='D:/FPS3D/FPSGAME'
$r4Root="$r4Project/SourceAssets/ModernTacticalSet20261113/CombatShirtR4"
$r4Log="$r4Root/Logs/$Label-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
$r4Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$r4Held=$false
try {
    Write-Output "R4_STAGE_QUEUED $Label"
    try {$r4Held=$r4Gate.WaitOne()} catch [Threading.AbandonedMutexException] {$r4Held=$true}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$r4Root/StageHostLean/TS01CombatR4.uproject" '/Engine/Maps/Entry' '-run=pythonscript' "-script=$Script" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-Multiprocess' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen' '-AssetGatherAll=false' '-asyncskinnedassetcompilation=0' '-asyncstaticmeshcompilation=0' '-asynctexturecompilation=0' "-abslog=$r4Log.log" *> "$r4Log.stdout.txt"
    $r4Exit=$LASTEXITCODE
    Write-Output "R4_STAGE_EXIT $r4Exit $r4Log"
    Get-Content -LiteralPath "$r4Log.stdout.txt" -Tail 8
    exit $r4Exit
} finally {
    if($r4Held){$r4Gate.ReleaseMutex()}
    $r4Gate.Dispose()
}
