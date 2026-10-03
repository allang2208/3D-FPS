$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$sourceDirectory = Join-Path $projectRoot 'SourceAssets\Baguette20261003'
$commandlet = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'

# The shared build wrapper waits for existing editors, games and builds. It
# does not stop them and never launches an editor or a gameplay session.
& (Join-Path $projectRoot 'Tools\Build\Build-SurvivalHUD20261003.ps1')
if (-not $?) { throw 'Native build did not complete; revised authoring files remain saved.' }

$deadline = (Get-Date).AddMinutes(60)
while (@(Get-Process -Name UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue).Count -gt 0) {
    if ((Get-Date) -ge $deadline) { throw 'Asset save window remains occupied. No running process was stopped.' }
    Start-Sleep -Seconds 20
}
$logFile = Join-Path $projectRoot ('Saved\Logs\BaguetteResizedImport-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$arguments = @(
    (Join-Path $projectRoot 'FPSGAME.uproject'),
    '-run=pythonscript',
    ('-script=' + (Join-Path $sourceDirectory 'import_baguette.py')),
    '-unattended', '-nop4', '-nosplash', '-nosound', '-NullRHI',
    ('-abslog=' + $logFile)
)
Write-Output "Saving revised baguette assets with a headless commandlet; log: $logFile"
& $commandlet @arguments *> (Join-Path $sourceDirectory 'commandlet_output.log')
if ($LASTEXITCODE -ne 0) {
    Get-Content -LiteralPath (Join-Path $sourceDirectory 'commandlet_output.log') -Tail 30
    throw "Baguette asset import failed with exit code $LASTEXITCODE. See $logFile"
}
$receipt = Get-Content -LiteralPath (Join-Path $sourceDirectory 'import_receipt.json') -Raw | ConvertFrom-Json
Write-Output ('Baguette assets saved: ' + $receipt.saved + '; dimensions cm: ' + ($receipt.dimensions_cm -join ', '))
Write-Output 'Source, inventory icon, native binaries and revised assets saved. No gameplay or tests were started.'
