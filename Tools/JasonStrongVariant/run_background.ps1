param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Name)
$ErrorActionPreference='Stop'
$jasonProject='D:/FPS3D/FPSGAME'
$jasonOutput=Join-Path $jasonProject ('SourceAssets/JasonStrong20261117/R2_LongLegs/'+$Name)
$jasonGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$jasonHeld=$false
try {
    Write-Output 'Queued for the shared asset batch.'
    try {$jasonHeld=$jasonGate.WaitOne(3600000)} catch [Threading.AbandonedMutexException] {$jasonHeld=$true;throw 'Previous asset batch ended abnormally; commandlet not started.'}
    if(-not $jasonHeld){throw 'Shared asset batch wait expired; commandlet not started.'}
    $jasonOwners=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')) -and ($_.CommandLine -match 'FPSGAME.uproject')})
    if($jasonOwners.Count){throw 'The project has an active engine process; retained it without starting another.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$jasonProject/FPSGAME.uproject" '-run=pythonscript' "-script=$Script" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$jasonOutput.log" *> "$jasonOutput.console.log"
    $jasonExit=$LASTEXITCODE
    Write-Output "Jason commandlet exit=$jasonExit"
    Get-Content -LiteralPath "$jasonOutput.console.log" -Tail 10
    exit $jasonExit
} finally {
    if($jasonHeld){$jasonGate.ReleaseMutex()}
    $jasonGate.Dispose()
}
