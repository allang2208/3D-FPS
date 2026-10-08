param([string]$Attempt='03')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromMinutes(40)) }
    catch [Threading.AbandonedMutexException] { $held=$true }
    if (-not $held) { throw 'Background import queue timed out.' }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'An editor is open; assets left untouched.' }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/import_assets.py" '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/import-commandlet-$Attempt.log" *> "$taskRoot/import-console-$Attempt.log"
    $code=$LASTEXITCODE
    if ($code -ne 0) { throw "UE import exited with $code. See import-commandlet-02.log." }
    $receipt=Get-Content -Raw -LiteralPath "$taskRoot/import_receipt.json" | ConvertFrom-Json
    if (-not $receipt.complete) { throw 'UE import has not saved every required asset.' }
    Write-Output 'XUANCHI_ASSETS_SAVED'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
