[CmdletBinding()]
param(
    [ValidateSet('Functional','Portal')][string]$Kind = 'Functional',
    [switch]$FromHills,
    [string]$Label = ('audit-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$project = Join-Path $projectRoot 'FPSGAME.uproject'
$outDir = Join-Path $projectRoot "Saved/GrassDenseValidation20260926/$Label"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$map = if ($Kind -eq 'Portal') { '/Game/GameMaps/DayNight_Lighting' } else { '/Game/GameMaps/L_GrassDeformDenseTest' }
if ($Kind -eq 'Portal' -and $FromHills) { $map = '/Game/GameMaps/L_TemperateHills_Initial' }
$runArgs = @(
    "`"$project`"", $map, '-game', '-windowed', '-RenderOffscreen', '-ResX=1280', '-ResY=720',
    '-unattended', '-nosound', '-NoSplash', '-ClearwaterNoMenu', "-Grass${Kind}Audit",
    "-GrassAuditLabel=$Label", "-ColdSteelProfile=GrassAudit-$Label", '-ExecCmds="t.MaxFPS 60"',
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
    "-abslog=`"$(Join-Path $outDir 'runtime.log')`""
)
if ($FromHills) { $runArgs += '-GrassPortalFromHills' }
$testProcess = Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' `
    -ArgumentList $runArgs -WindowStyle Hidden -PassThru
Write-Output "Started owned $Kind audit process $($testProcess.Id); evidence $outDir"
$maximum = if ($Kind -eq 'Portal') { 780 } else { 300 }
if (-not $testProcess.WaitForExit($maximum * 1000)) {
    # This PID is the exact test process created above; never touch an existing user session.
    Stop-Process -Id $testProcess.Id
    throw "Owned audit exceeded ${maximum}s; evidence retained in $outDir"
}
$testProcess.Refresh()
$report = Join-Path $outDir 'results.txt'
if (Test-Path -LiteralPath $report) { Get-Content -LiteralPath $report }
else { throw "Audit exited without a report; read $outDir/runtime.log" }
if (-not (Select-String -LiteralPath $report -Pattern '^COMPLETE ' -Quiet)) { throw 'Audit did not complete' }
exit $testProcess.ExitCode
