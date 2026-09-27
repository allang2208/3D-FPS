param([string]$Label=('BowSightCaptureAudit_'+[DateTime]::Now.ToString('yyyyMMdd_HHmmss')))
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
if ($Label -notmatch '^BowSightCaptureAudit_[A-Za-z0-9_]+$') { throw 'Use an isolated screenshot profile label.' }
$out=Join-Path $projectRoot ('Saved\BowRingSight20260927\'+$Label)
if (Test-Path -LiteralPath $out) { throw 'Choose a fresh screenshot label.' }
New-Item -ItemType Directory -Path $out -Force | Out-Null
$args=@(('"'+$projectRoot+'\FPSGAME.uproject"'),'/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
    '-game','-windowed','-RenderOffscreen','-ForceRes','-ResX=1920','-ResY=1080','-unattended','-nosplash','-nosound',
    '-d3d12','-ClearwaterNoMenu',('-ColdSteelProfile='+$Label),'-ExecCmds="t.MaxFPS 60,r.SetRes 1920x1080w,DisableAllScreenMessages,fps.Bow.CaptureSight"',
    ('-abslog="'+$out+'\runtime.log"'))
$proc=Start-Process 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
Write-Output ('[capture] Isolated offscreen game PID '+$proc.Id+' output '+$out)
$proc.WaitForExit()
Write-Output ('[capture] Exit '+$proc.ExitCode)
if ($proc.ExitCode -ne 0) { throw 'Screenshot process did not complete; see runtime.log' }
foreach ($name in @('01_hip_ready.png','02_ads_ready.png','03_ads_full_draw.png')) {
    if (-not (Test-Path -LiteralPath (Join-Path $out $name))) { throw ('Missing screenshot '+$name) }
}
Write-Output ('[done] '+$out)
