param(
    [Parameter(Mandatory = $true)][string]$SpecPath,
    [Parameter(Mandatory = $true)][string]$ReceiptPath,
    [string]$ProjectRoot = 'D:/FPS3D/FPSGAME',
    [string]$UeCmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
)

$ErrorActionPreference = 'Stop'

$resolvedSpec = (Resolve-Path -LiteralPath $SpecPath).Path
$receiptDir = Split-Path -Parent $ReceiptPath
if ($receiptDir) {
    New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
}
$logPath = Join-Path $receiptDir ('ue-audio-import-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')

$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try {
        $held = $gate.WaitOne()
    } catch [Threading.AbandonedMutexException] {
        $held = $true
    }

    while ($true) {
        $busy = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('cl.exe', 'link.exe', 'UnrealBuildTool.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'D:[\/]FPS3D[\/]FPSGAME')
        })
        if (-not $busy.Count) { break }
        try {
            Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop
        } catch [System.TimeoutException] {
        } catch {
            if (Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue) { throw }
        }
    }

    $prevSpec = $env:FPSGAME_AUDIO_IMPORT_SPEC
    $prevReceipt = $env:FPSGAME_AUDIO_IMPORT_RECEIPT
    $env:FPSGAME_AUDIO_IMPORT_SPEC = $resolvedSpec
    $env:FPSGAME_AUDIO_IMPORT_RECEIPT = $ReceiptPath
    try {
        $scriptPath = "$ProjectRoot/Tools/AudioPipeline/import_audio_ue.py"
        $ueArgs = @(
            "$ProjectRoot/FPSGAME.uproject",
            '-unattended',
            '-nop4',
            '-nosplash',
            '-nosound',
            '-nullrhi',
            "-abslog=$logPath",
            '-run=pythonscript',
            "-script=$scriptPath"
        )
        & $UeCmd @ueArgs *> ($logPath + '.stdout.txt')
        $exitCode = $LASTEXITCODE
    } finally {
        $env:FPSGAME_AUDIO_IMPORT_SPEC = $prevSpec
        $env:FPSGAME_AUDIO_IMPORT_RECEIPT = $prevReceipt
    }

    if ($exitCode -ne 0 -or -not (Test-Path -LiteralPath $ReceiptPath)) {
        Get-Content -LiteralPath ($logPath + '.stdout.txt') -Tail 25 -ErrorAction SilentlyContinue
        throw "Headless UE5 audio import failed (exit=$exitCode). Log: $logPath"
    }
    Write-Host "UE5 audio import completed. Receipt: $ReceiptPath"
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
