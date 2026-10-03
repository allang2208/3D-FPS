param([int]$WaitSeconds = 900, [switch]$BuildOnly, [string]$BuildLogName = 'build-editor-v16.log')
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$caseRoot = $PSScriptRoot
$logs = Join-Path $projectRoot 'Saved\BowNockFlow20260927'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Wait-ForWorkspace {
    $deadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
    $announced = $false
    while ($true) {
        $busy = Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -match '^UnrealEditor.*\.exe$' -and
                (-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME')) -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -match '^(cl|link)\.exe$') -or
            ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')
        }
        if (-not $busy) { return }
        if (-not $announced) {
            Write-Output ('[queue] Waiting for running UE/build processes: ' + ($busy.ProcessId -join ', '))
            $announced = $true
        }
        if ([DateTime]::UtcNow -ge $deadline) {
            throw 'Workspace is still busy; source and authored bow assets are preserved. No running process was closed.'
        }
        Start-Sleep -Seconds 5
    }
}

Wait-ForWorkspace
$modulePath = Join-Path $projectRoot 'Binaries\Win64\UnrealEditor-FPSGAME.dll'
$module = [IO.File]::Open($modulePath, 'Open', 'Read', 'None')
$module.Dispose()
Write-Output '[build] Building FPSGAMEEditor without launching UE.'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' `
    FPSGAMEEditor Win64 Development "$projectRoot\FPSGAME.uproject" `
    *> "$logs\$BuildLogName"
if ($LASTEXITCODE -ne 0) { throw "Editor build did not complete; see $logs\$BuildLogName" }
Write-Output '[build] FPSGAMEEditor succeeded. No gameplay test was run.'


