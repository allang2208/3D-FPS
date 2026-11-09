param([Parameter(Mandatory=$true)][string]$Script)
$ErrorActionPreference = 'Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$root = (Resolve-Path "$PSScriptRoot/../..").Path
$log = Join-Path $root "Saved/Logs/M249_$([IO.Path]::GetFileNameWithoutExtension($Script)).log"
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if (!$held) { throw 'Asset bridge busy' }
    $engine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    & $engine "$root/FPSGAME.uproject" '-run=pythonscript' "-script=$PSScriptRoot/$Script" '-unattended' '-NoSplash' '-NoSound' '-NullRHI' '-NoP4' '-UTF8Output' "-abslog=$log" *> "$log.console"
    $result=$LASTEXITCODE
    Get-Content -LiteralPath $log -Tail 15
    exit $result
} finally { if ($held) {$gate.ReleaseMutex()}; $gate.Dispose() }
