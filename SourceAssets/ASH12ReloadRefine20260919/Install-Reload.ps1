param(
    [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8'
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$projectFile = Join-Path $projectRoot 'FPSGAME.uproject'
$projectEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
    [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
})
if ($projectEditors.Count -gt 0) {
    throw 'Save and close the FPSGAME editor before importing and building. No processes were stopped.'
}

# Finish the complete module graph before launching a process that loads it.
& (Join-Path $projectRoot 'Tools/Build/Build-Editor.ps1') -EngineRoot $EngineRoot

$commandlet = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$importScript = Join-Path $PSScriptRoot 'import_reload.py'
$importLog = Join-Path $PSScriptRoot 'import-final.log'
& $commandlet $projectFile -run=pythonscript "-script=$importScript" -unattended -nop4 -nosplash -NullRHI "-abslog=$importLog"
if ($LASTEXITCODE -ne 0) {
    throw "ASH-12 animation import failed. See $importLog"
}

Write-Output 'ASH-12 reload assets imported and Editor modules built. Open the project to test manually.'
