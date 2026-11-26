param(
    [string]$Editor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',
    [string]$OutputDirectory='',
    [int]$TimeoutSeconds=180
)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if(!$OutputDirectory){$OutputDirectory=Join-Path $projectRoot ('Saved/EnhancementEscrowAudit/'+(Get-Date -Format 'yyyyMMdd-HHmmss'))}
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$profile='EnhancementEscrowAudit_'+[Guid]::NewGuid().ToString('N')
$userDir=Join-Path $OutputDirectory 'user'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(!$held){throw 'Shared UE batch remained busy.'}
# Background authority/serialization checks only. This does not certify UDP,
# same-player reconnect, UI dragging or ritual rendering.
foreach($phase in @('write','reload')){
    $logPath=Join-Path $OutputDirectory ($phase+'.log')
    $resultPath=Join-Path $OutputDirectory ($phase+'.json')
    $loadSwitch=if($phase -eq 'reload'){' -LoadOnly'}else{''}
    $arguments='"{0}/FPSGAME.uproject" -run=EnhancementEscrowAudit -Profile={1} -Output="{2}" -abslog="{3}" -unattended -nullrhi -nosound -NoSplash -multiprocess -NoShaderCompile -UserDir="{5}/"{4}' -f $projectRoot,$profile,$resultPath,$logPath,$loadSwitch,$userDir
    $audit=Start-Process -FilePath $Editor -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit($TimeoutSeconds*1000)){$audit.Kill();throw "Owned escrow audit timed out: $logPath"}
    if(!(Test-Path -LiteralPath $resultPath)){throw "No escrow result: $logPath (exit $($audit.ExitCode))"}
    $result=Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    if($audit.ExitCode -ne 0 -or $result.failures -ne 0 -or $result.checks.Count -lt 1){throw "Escrow audit failed: $logPath (exit $($audit.ExitCode))"}
    Write-Output "PASS $phase $($result.checks.Count) checks: $resultPath"
}

}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
