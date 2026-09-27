[CmdletBinding()]
param([string]$Label = ('response-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference = 'Stop'
$grassProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$grassOutput = Join-Path $grassProjectRoot "Saved/GrassResponseAudit20260927/$Label"
New-Item -ItemType Directory -Path $grassOutput -Force | Out-Null
$grassArguments = @(
    "`"$(Join-Path $grassProjectRoot 'FPSGAME.uproject')`"", '/Game/GameMaps/L_GrassDeformDenseTest',
    '-game', '-windowed', '-RenderOffscreen', '-ResX=1280', '-ResY=720', '-unattended', '-nosound',
    '-NoSplash', '-ClearwaterNoMenu', '-GrassResponseAudit', '-UseFixedTimeStep', '-FPS=60',
    "-GrassAuditLabel=$Label", "-ColdSteelProfile=GrassResponseAudit-$Label", '-ExecCmds="t.MaxFPS 60"',
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
    "-abslog=`"$(Join-Path $grassOutput 'runtime.log')`""
)
$grassProcess = Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' `
    -ArgumentList $grassArguments -WindowStyle Hidden -PassThru
Write-Output "Owned grass response process $($grassProcess.Id); output $grassOutput"
$grassDeadline = (Get-Date).AddSeconds(300)
while (-not $grassProcess.WaitForExit(1000)) {
    if ((Get-Date) -gt $grassDeadline) {
        Stop-Process -Id $grassProcess.Id
        throw 'Only the owned response capture process was stopped after timeout; evidence retained.'
    }
}
$grassProcess.Refresh()
$grassReport = Join-Path $grassOutput 'results.txt'
if (-not (Test-Path -LiteralPath $grassReport)) { throw 'Response audit exited without results.txt' }
Get-Content -LiteralPath $grassReport
if (-not (Select-String -LiteralPath $grassReport -Pattern '^COMPLETE ' -Quiet)) { throw 'Response audit did not complete' }
exit $grassProcess.ExitCode
