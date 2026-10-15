$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $taskProject 'SourceAssets/IncineratorBossM66/NetworkAudioReviewV18'
$taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor|UnrealEditor|-LiveCoding')
})
if($taskBusy.Count){throw 'Project editor or Editor build active; nothing stopped.'}
$taskRun=Join-Path $taskRoot ('checks-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $taskRun -Force | Out-Null
$taskArgs=@(
    ('"'+$taskProject+'/FPSGAME.uproject"'),'/Engine/Maps/Entry',
    '-unattended','-NullRHI','-nosound','-nosplash','-nop4','-NoLiveCoding','-UTF8Output',
    ('"-UserDir='+$taskRun+'/user"'),('"-abslog='+$taskRun+'/engine.log"'),
    ('"-ReportExportPath='+$taskRun+'/report"'),
    '"-ExecCmds=Automation RunTests FPSGAME.Monsters.M66.NetworkClockAndControl"',
    '"-TestExit=Automation Test Queue Empty"'
)
$taskProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $taskArgs -WorkingDirectory $taskProject -WindowStyle Hidden -PassThru
$taskDeadline=(Get-Date).AddMinutes(6)
while(-not $taskProcess.WaitForExit(5000)) {
    if((Get-Date)-gt $taskDeadline){throw ('Check process still running; retained PID '+$taskProcess.Id+' log '+$taskRun+'/engine.log')}
}
$taskProcess.Refresh()
[ordered]@{pid=$taskProcess.Id;exit_code=$taskProcess.ExitCode;run=$taskRun;test='FPSGAME.Monsters.M66.NetworkClockAndControl';real_multiplayer=$false;audio_audition=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskRun 'process.json') -Encoding utf8
if($taskProcess.ExitCode -ne 0){throw ('M66 check process exit '+$taskProcess.ExitCode+'; see '+$taskRun)}
Write-Output ('M66 check process completed; inspect test result in '+$taskRun)
