[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$project = Join-Path $projectRoot 'FPSGAME.uproject'
$editorCmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$holders = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'UnrealEditor*.exe' -and
    ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -like '*FPSGAME.uproject*')
})
if ($holders.Count -gt 0) {
    throw 'FPSGAME is open. Save and close it before background map authoring; no process was stopped.'
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logDir = Join-Path $projectRoot 'Saved/Logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir "GrassDenseTest-$stamp.log"
$scriptPath = Join-Path $PSScriptRoot 'author_dense_test_level.py'
& $editorCmd $project '-run=pythonscript' "-script=$scriptPath" `
    '-unattended' '-nosplash' '-nop4' '-AllowCommandletRendering' `
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$log"
if ($LASTEXITCODE -ne 0) { throw "Grass map authoring failed. See $log" }
Write-Output "Grass map authoring finished. Runtime testing remains manual. Log: $log"
