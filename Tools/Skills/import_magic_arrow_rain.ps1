$ErrorActionPreference='Stop'
$rainRoot='D:/FPS3D/FPSGAME'
$rainGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$rainHeld=$false
try {
    try {$rainHeld=$rainGate.WaitOne([TimeSpan]::FromMinutes(10))}
    catch [Threading.AbandonedMutexException] {$rainHeld=$true}
    if(-not $rainHeld){throw 'UE authoring batch is occupied'}
    # The recipe owns a new skill directory; it never saves loaded stock/other skill packages.
    $rainScript="$rainRoot/Tools/Skills/build_magic_arrow_rain_assets.py"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$rainRoot/FPSGAME.uproject" -run=pythonscript "-script=$rainScript" -unattended -nop4 -nosplash -nullrhi -multiprocess "-abslog=$rainRoot/Saved/MagicArrowRain20261026/import.log" *> "$rainRoot/Saved/MagicArrowRain20261026/import-console.log"
    $rainResult=$LASTEXITCODE
    Get-Content -LiteralPath "$rainRoot/Saved/MagicArrowRain20261026/import-console.log" -Tail 5
    exit $rainResult
} finally {
    if($rainHeld){$rainGate.ReleaseMutex()};$rainGate.Dispose()
}
