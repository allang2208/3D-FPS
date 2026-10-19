$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskOutput = "$taskRoot/SourceAssets/StaffLivingEmployees20261017"
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    $taskHeld = $taskGate.WaitOne([TimeSpan]::FromSeconds(60))
    if (-not $taskHeld) { throw 'UE asset batch is busy; no process started.' }
    $taskPrior = @(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject') })
    foreach ($taskProcess in $taskPrior) {
        try { [Diagnostics.Process]::GetProcessById($taskProcess.ProcessId).WaitForExit() } catch [ArgumentException] { }
    }
    # The active editor has never loaded these three destination packages.
    # Existing donor packages are read only; the Python script saves only new BPs.
    foreach ($taskName in @('LivingStaffMale','LivingStaffFemaleA','LivingStaffFemaleB')) {
        if (Test-Path -LiteralPath "$taskRoot/Content/Monsters/StaffLiving/BP_$taskName.uasset") {
            throw "Destination already exists; preserve it: $taskName"
        }
    }
    $taskLog = "$taskOutput/Logs/create-assets-commandlet.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/Tools/StaffLivingEmployees/install_assets.py" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$taskOutput/CommandletUser/" "-abslog=$taskLog" *> "$taskOutput/Logs/create-assets-stdout.log"
    $taskExit = $LASTEXITCODE
    @{ exit_code=$taskExit; log=$taskLog; runtime_tested=$false; rendered=$false; scope='Three new StaffLiving Blueprints only; donor packages not saved' } | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/asset_process.json" -Encoding UTF8
    if ($taskExit -ne 0) { throw "Employee asset commandlet exited with code $taskExit; see $taskLog" }
    Write-Output 'Three employee Blueprints saved by the background commandlet.'
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
