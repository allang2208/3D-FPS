param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')

$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$statusFile = Join-Path $PSScriptRoot 'native_build_status.json'
$buildScript = Join-Path $projectRoot 'Tools/Build/Build-Editor.ps1'
$buildOutput = Join-Path $PSScriptRoot 'native_build_output.log'

function Write-Status([string]$Phase, [string]$Detail = '') {
    $record = [ordered]@{
        revision = 'AggressionV5'
        phase = $Phase
        detail = $Detail
        timestamp = (Get-Date).ToString('o')
        native_build_pending = ($Phase -ne 'complete')
        runtime_tested = $false
    }
    [IO.File]::WriteAllText($statusFile, ($record | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
}

function Get-BuildBlocker {
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='UnrealBuildTool.exe' OR Name='cl.exe'")
    foreach ($process in $processes) {
        if ($process.Name -like 'UnrealEditor*' -and
            ([string]::IsNullOrWhiteSpace($process.CommandLine) -or $process.CommandLine -match 'FPSGAME\.uproject')) {
            return 'waiting for the existing FPSGAME editor or commandlet to exit'
        }
        if ($process.Name -eq 'UnrealBuildTool.exe' -or
            ($process.Name -eq 'dotnet.exe' -and $process.CommandLine -match 'UnrealBuildTool')) {
            return 'waiting for the current Unreal native build to finish'
        }
        if ($process.Name -eq 'cl.exe' -and $process.CommandLine -match 'FPSGAME[\\/]Intermediate[\\/]Build') {
            return 'waiting for the current FPSGAME compiler to finish'
        }
    }
    return ''
}

try {
    $lastBlocker = ''
    while ($true) {
        $blocker = Get-BuildBlocker
        if (-not $blocker) { break }
        if ($blocker -ne $lastBlocker) {
            Write-Status 'waiting' $blocker
            $lastBlocker = $blocker
        }
        # No UE/MCP gate is held while waiting; no processes are stopped or started.
        Start-Sleep -Seconds 15
    }
    Write-Status 'building' 'ordinary FPSGAMEEditor build; no editor launch'
    & $buildScript -EngineRoot $EngineRoot *> $buildOutput
    if ($LASTEXITCODE -ne 0) { throw "Editor build exited with code $LASTEXITCODE" }
    Write-Status 'complete' 'ordinary editor modules saved; gameplay testing remains manual'
    exit 0
}
catch {
    Write-Status 'failed' $_.Exception.Message
    Add-Content -LiteralPath $buildOutput -Value $_.Exception.Message -Encoding UTF8
    exit 1
}
