param(
    [string[]]$Targets = @('FPSGAMEEditor', 'FPSGAME'),
    [string]$OutputDirectory = 'D:/FPS3D/FPSGAME/Saved/DeformationResidencyBuild20261029'
)
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskOutput = $OutputDirectory
New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    try { $taskHeld = $taskGate.WaitOne([TimeSpan]::FromMinutes(10)) }
    catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    if (-not $taskHeld) { throw 'UE batch remains occupied; no build started.' }
    foreach ($taskTarget in $Targets) {
        $taskBuilds = @(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'
        })
        foreach ($taskProcess in $taskBuilds) {
            try { [Diagnostics.Process]::GetProcessById($taskProcess.ProcessId).WaitForExit() }
            catch [ArgumentException] {}
        }
        $taskOwners = @(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME') -or
            $_.Name -match '^FPSGAME(-Win64-.+)?\.exe$'
        })
        if ($taskOwners.Count) { throw 'Preserving an existing FPSGAME editor/game; no binary replacement attempted.' }
        $taskModes = @()
        $taskDefinitions = "$taskRoot/Intermediate/Build/Win64/x64/$taskTarget/Development/Core/SharedDefinitions.Core.Cpp20.h"
        if ((Test-Path -LiteralPath $taskDefinitions) -and
            [IO.File]::ReadAllText($taskDefinitions) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$') {
            $taskModes += '-NoLiveCoding'
        }
        $taskLog = "$taskOutput/build-$taskTarget.log"
        # This installation's UE5Rules lacks FabToolset. Scope the workaround to
        # Editor; Fab has no runtime module and Game rejects this target override.
        $taskOverrides = @()
        if ($taskTarget -eq 'FPSGAMEEditor') { $taskOverrides += '-DisablePlugin=Fab' }
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE @taskModes @taskOverrides -MaxParallelActions=2 "-Log=$taskLog" *> "$taskOutput/build-$taskTarget-stdout.log"
        $taskExit = $LASTEXITCODE
        @{ target = $taskTarget; exit_code = $taskExit; log = $taskLog; extra_arguments = $taskOverrides; runtime_tested = $false; editor_started = $false; completed_utc = [DateTime]::UtcNow.ToString('o') } |
            ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/build-$taskTarget.receipt.json" -Encoding utf8
        if ($taskExit -ne 0) { throw "Build failed: $taskLog" }
        Write-Output "$taskTarget build succeeded."
    }
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
