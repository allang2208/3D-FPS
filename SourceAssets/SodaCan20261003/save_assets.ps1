$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$sourceDirectory = Join-Path $projectRoot 'SourceAssets\SodaCan20261003'
$commandlet = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$deadline = (Get-Date).AddMinutes(60)
$announced = $false
while ($true) {
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='FPSGAME.exe'")
    $busy = @($processes | Where-Object {
        $_.Name -ne 'dotnet.exe' -or $_.CommandLine -match 'UnrealBuildTool'
    })
    if ($busy.Count -eq 0) { break }
    if (-not $announced) { Write-Output 'Waiting for the background asset save window. No process will be stopped.'; $announced = $true }
    if ((Get-Date) -ge $deadline) { throw 'The asset save window remains occupied. Authored sources were preserved.' }
    Start-Sleep -Seconds 20
}
$logFile = Join-Path $projectRoot ('Saved\Logs\SodaCanImport-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$arguments = @(
    (Join-Path $projectRoot 'FPSGAME.uproject'),
    '-run=pythonscript',
    ('-script=' + (Join-Path $sourceDirectory 'import_soda.py')),
    '-unattended', '-nop4', '-nosplash', '-nosound', '-NullRHI',
    ('-abslog=' + $logFile)
)
Write-Output "Saving soda assets with a headless commandlet; log: $logFile"
& $commandlet @arguments *> (Join-Path $sourceDirectory 'commandlet_output.log')
if ($LASTEXITCODE -ne 0) {
    Get-Content -LiteralPath (Join-Path $sourceDirectory 'commandlet_output.log') -Tail 30
    throw "Soda asset import failed with exit code $LASTEXITCODE. See $logFile"
}
$receipt = Get-Content -LiteralPath (Join-Path $sourceDirectory 'import_receipt.json') -Raw | ConvertFrom-Json
Write-Output ('Soda assets saved: ' + $receipt.saved + '; mesh: ' + $receipt.mesh)
Write-Output 'No editor UI, game, or tests were launched.'
