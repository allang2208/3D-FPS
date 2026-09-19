param([ValidateSet(30,60,144)][int]$Fps=60, [string]$Label='', [switch]$CaptureFrames)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if(!$Label){$Label='slide-combat-'+$Fps+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')}
if($Label -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Invalid label'}
$outputDir=Join-Path $projectRoot ('Saved/GunplayUpgrade/'+$Label)
if(Test-Path -LiteralPath $outputDir){throw "Output exists: $outputDir"}
$logPath=Join-Path $projectRoot ('Saved/'+$Label+'.log')
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX=1280 -ResY=720 -ForceRes -unattended -nosplash -SlideCombatAudit -GunplayLabel={1} -ColdSteelProfile={1} -UseFixedTimeStep -FPS={2} -abslog="{3}"' -f $projectRoot,$Label,$Fps,$logPath
if($CaptureFrames){$arguments+=' -GunplayCaptureFrames'}
$auditProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
Write-Output "Slide combat audit PID=$($auditProcess.Id), label=$Label"
if(!$auditProcess.WaitForExit(180000)){
    $auditProcess.Kill()
    throw "Owned slide audit timed out: $logPath"
}
$assertions=Get-Content -LiteralPath (Join-Path $outputDir 'assertions.log')
$pass=@($assertions | Where-Object {$_ -match '^GUNPLAY_ASSERT PASS '}).Count
$fail=@($assertions | Where-Object {$_ -match '^GUNPLAY_ASSERT FAIL '}).Count
$complete=@($assertions | Where-Object {$_ -eq 'GUNPLAY_ACCEPTANCE_COMPLETE failures=0'}).Count -eq 1
$summary=[ordered]@{label=$Label;simulation_hz=$Fps;pass=$pass;fail=$fail;complete=$complete;exit_code=$auditProcess.ExitCode;log=$logPath;note='Real controller input in a rendered standalone process; fixed simulation step, not measured FPS.'}
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'result.json') -Encoding utf8
$summary | ConvertTo-Json | Write-Output
if($auditProcess.ExitCode -ne 0 -or !$complete -or $fail -gt 0 -or $pass -eq 0){exit 1}
