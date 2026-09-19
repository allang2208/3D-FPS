param([string]$Label='RifleSprintAudit-final60',[int]$Fps=60,[switch]$CaptureFrames)
$ErrorActionPreference='Stop'
if ($Label -notmatch '^RifleSprintAudit-[a-zA-Z0-9_-]+$') { throw 'Use an isolated RifleSprintAudit label' }
$taskProject='D:/FPS3D/FPSGAME'
$taskOut=Join-Path $taskProject ('Saved/RifleSprintAudit/'+$Label)
if (Test-Path -LiteralPath $taskOut) { throw 'Choose a fresh output label' }
$taskLog=Join-Path $PSScriptRoot ($Label+'.log')
$taskArguments=@(
 ('"'+$taskProject+'/FPSGAME.uproject"'),'/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
 '-game','-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-unattended','-nosplash','-nosound',
 '-GunplayAudit','-RifleSprintAudit',('-ColdSteelProfile='+$Label),('-GunplayLabel='+$Label),'-FixedSeed',
 '-d3d11','-UseFixedTimeStep',('-FPS='+$Fps),'-DisablePlugins=ModelContextProtocol,AllToolsets',
 '-EnablePlugins=GameFeatures',('-abslog="'+$taskLog+'"'))
if ($CaptureFrames) {$taskArguments+='-GunplayCaptureFrames'}
$taskProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArguments -WindowStyle Hidden -PassThru
Write-Output "Rifle sprint runtime process $($taskProcess.Id), fixed simulation $Fps Hz"
$taskProcess.WaitForExit()
Get-Content (Join-Path $taskOut 'results.log') -Tail 12
Write-Output "RUNTIME_EXIT=$($taskProcess.ExitCode)"
exit $taskProcess.ExitCode
