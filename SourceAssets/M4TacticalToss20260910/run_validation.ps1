param(
    [ValidateSet(30,60,144)][int]$Fps=60,
    [string]$Label='m4-rig-isolated60',
    [switch]$CaptureFrames,
    [switch]$SprintPreview,
    [switch]$EquipPreview,
    [switch]$CaptureAudio,
    [ValidateSet(10,20,30,60)][int]$CaptureHz=10,
    [ValidateSet(640,1280)][int]$PreviewWidth=1280,
    [switch]$D3D12
)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
if ($Label -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid label' }
$outputDir=Join-Path $projectRoot ('Saved/GunplayUpgrade/'+$Label)
if (Test-Path -LiteralPath $outputDir) { throw 'Choose a fresh label' }
$logPath=Join-Path $PSScriptRoot ('runtime-'+$Label+'.log')
$rhi=if ($D3D12) {'-d3d12'} else {'-d3d11'}
$arguments=@(
    ('"'+$projectRoot+'/FPSGAME.uproject"'),
    '/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
    '-game','-windowed','-RenderOffscreen',('-ResX='+$PreviewWidth),('-ResY='+($PreviewWidth*9/16)),'-unattended','-nosplash',
    '-GunplayAudit',('-ColdSteelProfile='+$Label),('-GunplayLabel='+$Label),'-FixedSeed',
    $rhi,('-abslog="'+$logPath+'"')
)
if ($CaptureFrames) { $arguments+=@('-GunplayCaptureFrames',('-GunplayCaptureHz='+$CaptureHz)) }
if ($SprintPreview) { $arguments+='-SprintPoseAudit' }
if ($EquipPreview) { $arguments+='-EquipFramingAudit' }
if ($CaptureAudio) { $arguments+=@('-GunplayCaptureAudio','-AudioMixer','-ini:Engine:[Audio]:UnfocusedVolumeMultiplier=1.0',('-ExecCmds="t.MaxFPS '+$Fps+',au.NeverDisableSubmixes 1"')) }
else { $arguments+=@('-UseFixedTimeStep',('-FPS='+$Fps)) }
$testProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
Write-Output "Rig acceptance process $($testProcess.Id), $Fps Hz, $rhi"
$testProcess.WaitForExit()
$assertions=Join-Path $outputDir 'assertions.log'
if (!(Test-Path -LiteralPath $assertions)) { throw "Missing assertions; inspect $logPath" }
$lines=Get-Content -LiteralPath $assertions
$passed=@($lines | Where-Object { $_ -match '^GUNPLAY_ASSERT PASS ' }).Count
$failed=@($lines | Where-Object { $_ -match '^GUNPLAY_ASSERT FAIL ' }).Count
$complete=@($lines | Where-Object { $_ -match '^GUNPLAY_ACCEPTANCE_COMPLETE failures=0 ' }).Count -eq 1
$clockMode=if ($CaptureAudio) {'Real time with FPS cap; actual mixer recording. Background audio enabled only for this validation process.'} else {'Fixed simulation rate, not measured FPS.'}
$result=[ordered]@{label=$Label;requested_hz=$Fps;clock_mode=$clockMode;rhi=$rhi;process_exit=$testProcess.ExitCode;pass=$passed;fail=$failed;completion_marker=$complete;assertions=$assertions;runtime_log=$logPath;note='Real rendered game, isolated clear floor, simulated controller inputs.'}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'result.json') -Encoding utf8
$result | ConvertTo-Json | Write-Output
if ($testProcess.ExitCode -ne 0 -or !$complete -or $failed -gt 0 -or $passed -eq 0) { exit 1 }
