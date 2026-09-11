param([ValidateSet('panoramic','scope2x','lpvo','muzzle')][string]$Kind='panoramic',[string]$Run='v1',[switch]$Reload)
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$out=Join-Path $PSScriptRoot "$Kind-$Run"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$phase=if($Reload){'reload'}else{'write'}
$log=Join-Path $out "$phase.log"
$flag=switch($Kind){'panoramic'{'-M4GunsmithAudit -AKMOpticAudit -PanoramicRedDotAudit'}'scope2x'{'-M4GunsmithAudit -AKMOpticAudit -PrismScope2XAudit'}'lpvo'{'-M4GunsmithAudit -AKMOpticAudit -LPVOAudit'}'muzzle'{'-MuzzleMigrationAudit -AKMMuzzleAudit'}}
$profile=if($Kind -eq 'muzzle'){"MuzzleMigrationAudit_AKM_$Run"}else{"M4GunsmithAudit_AKM_$($Kind)_$Run"}
if($Reload){$flag+=' -M4GunsmithLoadAudit'}
$args='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -Multiprocess -RenderOffscreen -windowed -ResX=1600 -ResY=900 -ForceRes -unattended -nosplash -ColdSteelProfile={1} {2} -ExecCmds="DisableAllScreenMessages,r.MotionBlurQuality 0,t.MaxFPS 60" -abslog="{3}"' -f $root,$profile,$flag,$log
$proc=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
Write-Output "AKM $Kind $phase process $($proc.Id)"
$deadline=[DateTime]::UtcNow.AddSeconds(240)
while(!$proc.WaitForExit(1000)){if([DateTime]::UtcNow -gt $deadline){throw "Owned process $($proc.Id) timed out"}}
$text=[IO.File]::ReadAllText($log)
if($proc.ExitCode -ne 0 -or $text -notmatch '(M4_GUNSMITH: COMPLETE|MUZZLE_MIGRATION_COMPLETE) checks=\d+ failures=0'){throw "AKM audit failed: $log"}
$folder=switch($Kind){'panoramic'{'PanoramicRedDotAudit/AKM'}'scope2x'{'PrismScope2XAudit/AKM'}'lpvo'{'LPVOAudit/AKM'}'muzzle'{'AKMMuzzleAudit'}}
Get-ChildItem -LiteralPath "$root/Saved/$folder" -File | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $out "$phase-$($_.Name)")}
Write-Output "AKM_OPTIC_RUNTIME_PASS $Kind $phase"
