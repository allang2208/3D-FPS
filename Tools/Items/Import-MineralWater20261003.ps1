$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\FPS3D\FPSGAME'
$taskProject = Join-Path $taskRoot 'FPSGAME.uproject'
$taskScript = Join-Path $taskRoot 'SourceAssets\MineralWater20261003\import_water.py'
$taskCommandlet = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskAnnounced = $false
while ($true) {
    $taskProcesses = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='FPSGAME.exe' OR Name='dotnet.exe'")
    $taskBusy = @($taskProcesses | Where-Object {
        $_.Name -eq 'UnrealEditor.exe' -or $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'FPSGAME.exe' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($taskBusy.Count -eq 0) { break }
    if (-not $taskAnnounced) { Write-Output 'Waiting for the current build/editor to release the asset import window.'; $taskAnnounced = $true }
    Start-Sleep -Seconds 10
}
$taskLog = Join-Path $taskRoot ('Saved\Logs\MineralWaterImport-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$taskArguments = '"' + $taskProject + '" -run=pythonscript -script="' + $taskScript + '" -unattended -nop4 -nosplash -nosound -nullrhi -multiprocess -DDC=InstalledNoZenLocalFallback -abslog="' + $taskLog + '"'
$taskProcess = Start-Process -FilePath $taskCommandlet -ArgumentList $taskArguments -WindowStyle Hidden -PassThru
Write-Output ('Mineral water import PID=' + $taskProcess.Id + '; log: ' + $taskLog)
$taskProcess.WaitForExit()
if ($taskProcess.ExitCode -ne 0) { throw ('Mineral water asset import failed; see ' + $taskLog) }
$taskReceiptPath = Join-Path $taskRoot 'SourceAssets\MineralWater20261003\import_receipt.json'
$taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
if (-not $taskReceipt.saved) { throw 'Mineral water asset import did not finish saving the assets.' }
Write-Output 'Mineral water meshes and materials imported and saved. No interactive editor or gameplay was launched.'
