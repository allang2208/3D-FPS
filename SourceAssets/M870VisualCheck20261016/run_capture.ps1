param([string]$Label='M870PoseAudit_20261016_a')
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$out=Join-Path $root ('Saved/M870PoseAudit/'+$Label)
if(Test-Path -LiteralPath $out){throw 'Choose a fresh capture label'}
$log=Join-Path $root ('SourceAssets/M870VisualCheck20261016/runtime-'+$Label+'.log')
$args=@(('"'+$root+'/FPSGAME.uproject"'),'/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation','-game','-windowed','-RenderOffscreen','-ResX=1280','-ResY=720','-unattended','-nosplash','-nosound','-ClearwaterNoMenu','-SkipStartupMenu','-M870PoseAudit',('-ColdSteelProfile='+$Label),('-GunplayLabel='+$Label),'-FixedSeed','-UseFixedTimeStep','-FPS=30','-d3d12',('-abslog="'+$log+'"'))
$p=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
@{process=$p.Id;label=$Label;output=$out;log=$log;started=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'SourceAssets/M870VisualCheck20261016/runtime_process.json') -Encoding utf8
Write-Output ('M870 visual capture process '+$p.Id)
$p.WaitForExit()
@{process=$p.Id;label=$Label;exit_code=$p.ExitCode;output=$out;log=$log;completed=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'SourceAssets/M870VisualCheck20261016/runtime_receipt.json') -Encoding utf8
if($p.ExitCode -ne 0){throw ('M870 capture exited '+$p.ExitCode)}
