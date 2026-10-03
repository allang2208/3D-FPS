$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$sourceDirectory = Join-Path $projectRoot 'SourceAssets\ConsumableAudio20261003'
$commandlet = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'

& (Join-Path $projectRoot 'Tools\Build\Build-SurvivalHUD20261003.ps1')
if (-not $?) { throw 'Native build did not complete; consumable audio sources remain saved.' }

$deadline = (Get-Date).AddMinutes(60)
$announced = $false
while ($true) {
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='FPSGAME.exe'")
    $busy = @($processes | Where-Object {
        $_.Name -ne 'dotnet.exe' -or $_.CommandLine -match 'UnrealBuildTool'
    })
    if ($busy.Count -eq 0) { break }
    if (-not $announced) { Write-Output 'Waiting for the background asset save window. No process will be stopped.'; $announced = $true }
    if ((Get-Date) -ge $deadline) { throw 'Audio import window remains occupied; no process was stopped.' }
    Start-Sleep -Seconds 20
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logFile = Join-Path $projectRoot ('Saved\Logs\ConsumableAudioImport-' + $stamp + '.log')
$outputFile = Join-Path $sourceDirectory ('commandlet-' + $stamp + '.log')
$arguments = @(
    (Join-Path $projectRoot 'FPSGAME.uproject'),
    '-run=pythonscript',
    ('-script=' + (Join-Path $sourceDirectory 'import_audio.py')),
    '-unattended', '-nop4', '-nosplash', '-nosound', '-NullRHI',
    ('-abslog=' + $logFile)
)
Write-Output "Importing and saving consumable sounds in the background; log: $logFile"
& $commandlet @arguments *> $outputFile
if ($LASTEXITCODE -ne 0) {
    Get-Content -LiteralPath $outputFile -Tail 25
    throw "Audio import failed with exit code $LASTEXITCODE. See $logFile"
}
$receipt = Get-Content -LiteralPath (Join-Path $sourceDirectory 'import_receipt.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Output ('Consumable sounds saved: ' + $receipt.saved + '; assets: ' + $receipt.assets.Count)
Write-Output 'Editor/Game binaries and four sounds saved. No editor UI, game or tests were started.'
