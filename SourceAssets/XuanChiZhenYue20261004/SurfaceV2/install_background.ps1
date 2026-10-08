param([string]$Attempt='01')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$held=$true}
    if (-not $held) {throw 'UE asset queue timed out.'}
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'An editor is open; use the existing editor bridge.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/install_assets.py" '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/import-commandlet-$Attempt.log" *> "$taskRoot/import-console-$Attempt.log"
    if ($LASTEXITCODE -ne 0) {throw "SurfaceV2 import failed. See import-commandlet-$Attempt.log."}
    Write-Output 'XUANCHI_SURFACE_V2_SAVED'
} finally {
    if ($held) {$gate.ReleaseMutex()};$gate.Dispose()
}
