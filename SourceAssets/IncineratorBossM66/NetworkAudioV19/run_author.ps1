param([string]$Script='install.py')
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME';$taskRoot=Join-Path $taskProject 'SourceAssets/IncineratorBossM66/NetworkAudioV19'
$taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor|UnrealEditor|-LiveCoding')
})
if($taskBusy.Count){throw 'Project editor or Editor build is active; nothing stopped.'}
$taskRun=Join-Path $taskRoot ('Records/author-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $taskRun -Force | Out-Null
$taskArgs=@(('"'+$taskProject+'/FPSGAME.uproject"'),'-run=PythonScript',('"-script='+$taskRoot+'/'+$Script+'"'),
    ('"-UserDir='+$taskRun+'/user"'),('"-abslog='+$taskRun+'/engine.log"'),'-NullRHI','-unattended','-nop4','-nosplash','-nosound','-NoLiveCoding',
    '"-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False"')
$taskProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $taskArgs -WorkingDirectory $taskProject -WindowStyle Hidden -PassThru
$taskDeadline=(Get-Date).AddMinutes(6)
while(-not $taskProcess.WaitForExit(5000)){if((Get-Date)-gt $taskDeadline){throw ('Author process still running; PID '+$taskProcess.Id+' log '+$taskRun)}}
$taskProcess.Refresh();[ordered]@{pid=$taskProcess.Id;exit_code=$taskProcess.ExitCode;script=$Script;log=$taskRun+'/engine.log'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskRun 'process.json') -Encoding utf8
if($taskProcess.ExitCode -ne 0){throw ('Author exit '+$taskProcess.ExitCode+'; '+$taskRun)}
Write-Output $taskRun
