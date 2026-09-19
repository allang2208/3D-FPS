param(
    [string]$Label='ReloadTiming60',
    [ValidateSet(30,60,144)][int]$Fps=60,
    [switch]$Capture,
    [switch]$Audio,
    [switch]$Video
)
$ErrorActionPreference='Stop'
if ($Label -notmatch '^ReloadTiming[a-zA-Z0-9_-]+$') { throw 'Use a unique ReloadTiming label' }
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut=Join-Path $taskRoot ('Saved/ReloadTiming/ColdSteel_'+$Label)
if(Test-Path -LiteralPath $taskOut){throw 'Choose a fresh label'}
New-Item -ItemType Directory -Path $taskOut | Out-Null
$taskLog=Join-Path $taskOut 'runtime.log'
$taskArgs=@(
    ('"'+$taskRoot+'/FPSGAME.uproject"'),
    '/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
    '-game','-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-unattended','-nosplash','-d3d11',
    '-ReloadTimingAudit',('-ColdSteelProfile='+$Label),('-abslog="'+$taskLog+'"')
)
if($Capture){$taskArgs+='-ReloadTimingCapture'}
if($Video){$taskArgs+=@('-ReloadTimingVideo','-ReloadTimingCapture')}
if($Audio){$taskArgs+=@('-ReloadTimingAudio','-AudioMixer','-ini:Engine:[Audio]:UnfocusedVolumeMultiplier=1.0',('-ExecCmds="t.MaxFPS '+$Fps+',au.NeverDisableSubmixes 1"'))}
else{$taskArgs+=@('-UseFixedTimeStep',('-FPS='+$Fps))}
$taskProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
Write-Output "Reload timing validation PID $($taskProcess.Id)"
$taskProcess.WaitForExit()
$taskLines=Get-Content -LiteralPath $taskLog
$taskFailed=@($taskLines | Where-Object {$_ -match 'RELOAD_TIMING FAIL'}).Count
$taskPassed=@($taskLines | Where-Object {$_ -match 'RELOAD_TIMING PASS'}).Count
$taskComplete=@($taskLines | Where-Object {$_ -match 'RELOAD_TIMING COMPLETE cases=24 failures=0'}).Count -eq 1
[ordered]@{label=$Label;requested_fps=$Fps;fixed_simulation=(!$Audio);exit=$taskProcess.ExitCode;pass=$taskPassed;fail=$taskFailed;complete=$taskComplete;log=$taskLog} | ConvertTo-Json | Tee-Object -FilePath (Join-Path $taskOut 'result.json')
if($taskProcess.ExitCode -ne 0 -or !$taskComplete -or $taskFailed){exit 1}
