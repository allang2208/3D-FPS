param([string]$Attempt='01', [int]$QueueWaitSeconds=120)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try {$held = $gate.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true; throw 'Previous UE batch state is unknown; this import was not started.'}
    if (-not $held) {
        Write-Output 'Waiting for the shared UE asset-authoring window.'
        try {$held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))} catch [Threading.AbandonedMutexException] {$held=$true; throw 'Previous UE batch state is unknown; this import was not started.'}
    }
    if (-not $held) {Write-Output 'Asset queue timed out; commandlet not started.'; exit 75}
    $editorBuilds = @(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.+FPSGAMEEditor'})
    if ($editorBuilds.Count -gt 0) {Write-Output 'Editor native build is active; commandlet not started.'; exit 76}
    $importLog = Join-Path $PSScriptRoot ('import-commandlet-' + $Attempt + '.log')
    $stdoutLog = Join-Path $PSScriptRoot ('import-stdout-' + $Attempt + '.log')
    $scriptPath = Join-Path $PSScriptRoot 'install_assets.py'
    $arguments = @((Join-Path $projectRoot 'FPSGAME.uproject'), '-run=pythonscript', "-script=$scriptPath", '-unattended', '-nop4', '-nosplash', '-NoSound', '-NoLiveCoding', '-RenderOffscreen', '-stdout', '-FullStdOutLogOutput', "-abslog=$importLog")
    $ErrorActionPreference = 'Continue'
    & $engine @arguments *> $stdoutLog
    $resultCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    @{exit_code=$resultCode;log=$importLog;stdout=$stdoutLog;editor_ui_started=$false;game_started=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'commandlet_receipt.json') -Encoding UTF8
    Write-Output "Material authoring exited $resultCode. Log: $importLog"
    exit $resultCode
} finally {
    if ($held) {$gate.ReleaseMutex()}
    $gate.Dispose()
}
