param([Parameter(Mandatory=$true)][string]$Run)
$ErrorActionPreference='Stop'
$auditProject=[IO.Path]::GetFullPath((Join-Path $Run 'Host/FPSGAME.uproject'))
if(-not (Test-Path -LiteralPath $auditProject)){throw 'Use the staged project from run.ps1'}
$auditOutput=Join-Path $Run 'AI'
New-Item -ItemType Directory -Force -Path $auditOutput | Out-Null
$auditGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$auditHeld=$false
try {
    try{$auditHeld=$auditGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$auditHeld=$true}
    if(-not $auditHeld){throw 'UE batch occupied; AI checks not started'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $auditProject '/Engine/Maps/Entry' `
        -unattended -nullrhi -nosound -nosplash -nop4 -NoAssetRegistryCacheWrite `
        '-ExecCmds=Automation RunTests FPSGAME.AI.Unknown' '-TestExit=Automation Test Queue Empty' `
        "-ReportExportPath=$auditOutput" "-UserDir=$auditOutput/User" "-abslog=$auditOutput/runtime.log" `
        '-ColdSteelProfile=UnknownAIAudit20261116' `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
        *> "$auditOutput/console.log"
    Write-Output "UNKNOWN_AI_CHECKS exit=$LASTEXITCODE output=$auditOutput"
    exit $LASTEXITCODE
} finally {if($auditHeld){$auditGate.ReleaseMutex()};$auditGate.Dispose()}
