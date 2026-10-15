param()
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $taskProject 'SourceAssets/IncineratorBossM66/SmallHandSeparationV09'
$taskEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor|UnrealEditor|-LiveCoding')
})
if($taskBusy.Count){throw 'Project editor or Editor DLL build is active; no process was stopped.'}
$taskRun=Join-Path $taskRoot ('Records/install-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $taskRun -Force | Out-Null
$taskLog=Join-Path $taskRun 'engine.log'
$taskUserDir=Join-Path $taskRun 'user'
$taskArgs=@(
    ('"'+(Join-Path $taskProject 'FPSGAME.uproject')+'"'),
    '-run=PythonScript',
    ('"-script='+(Join-Path $taskRoot 'install_headless.py')+'"'),
    ('"-UserDir='+$taskUserDir+'"'),
    ('"-abslog='+$taskLog+'"'),
    '-NullRHI','-unattended','-nop4','-nosplash','-nosound','-NoLiveCoding','-UTF8Output'
)
$taskPrevious=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskProc=Start-Process -FilePath $taskEngine -ArgumentList $taskArgs -WorkingDirectory $taskProject -WindowStyle Hidden -PassThru
    $taskDeadline=(Get-Date).AddMinutes(6)
    while(-not $taskProc.WaitForExit(5000)) {
        if((Get-Date)-gt $taskDeadline){throw ('M66 import still running; retained owned process '+$taskProc.Id+' and log '+$taskLog)}
    }
    $taskProc.Refresh()
    [ordered]@{pid=$taskProc.Id;exit_code=$taskProc.ExitCode;log=$taskLog;runtime_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskRun 'process.json') -Encoding utf8
    if($taskProc.ExitCode -ne 0){throw ('M66 commandlet exit '+$taskProc.ExitCode+'; log '+$taskLog)}
    Write-Output ('M66 import process completed: '+$taskLog)
} finally {$env:UE_SKIP_UBT_SDK_SETUP=$taskPrevious}
