param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runRoot=Join-Path $projectRoot ('Saved/AcquisitionNetworkAudit/run-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$userDirectory=Join-Path $runRoot 'user'
New-Item -ItemType Directory -Force -Path $userDirectory | Out-Null
$logPath=Join-Path $runRoot 'commandlet.log'
$previousSdkSetup=$env:UE_SKIP_UBT_SDK_SETUP
$env:UE_SKIP_UBT_SDK_SETUP='1'
try {
    $arguments='"{0}/FPSGAME.uproject" -run=ColdSteelAcquisitionAudit -AcquisitionAuditRoot="{1}" -UserDir="{2}/" -abslog="{3}" -NullRHI -unattended -nosplash -nosound -NoLiveCoding -UTF8Output' -f $projectRoot,$runRoot,$userDirectory,$logPath
    $auditProcess=Start-Process -FilePath (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Write-Output "Acquisition audit PID=$($auditProcess.Id) Output=$runRoot"
    $deadline=[DateTime]::UtcNow.AddMinutes(5)
    while(!$auditProcess.WaitForExit(1000)) {
        if([DateTime]::UtcNow -gt $deadline) { $auditProcess.Kill();throw "Owned acquisition audit timed out: $logPath" }
    }
    $exitCode=$auditProcess.ExitCode
    $reportPath=Join-Path $runRoot 'report.txt'
    if($exitCode -ne 0 -or !(Test-Path -LiteralPath $reportPath)) { throw "Acquisition audit failed (exit $exitCode): $logPath" }
    $report=[IO.File]::ReadAllText($reportPath)
    if($report -notmatch 'COMPLETE checks=\d+ failures=0' -or $report -match '(?m)^FAIL ') { throw "Acquisition assertions failed: $reportPath" }
    Write-Output ($report.Trim().Split("`n")[-1])
    Write-Output "Report: $reportPath"
} finally { $env:UE_SKIP_UBT_SDK_SETUP=$previousSdkSetup }
