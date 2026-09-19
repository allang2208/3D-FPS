$ErrorActionPreference='Stop'
$stockRoot='D:/FPS3D/FPSGAME'
$stockUE='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$stockOut=Join-Path $PSScriptRoot 'final-runtime'
if(Test-Path -LiteralPath $stockOut){throw 'Final runtime output already exists'}
New-Item -ItemType Directory -Path $stockOut | Out-Null
foreach($weapon in @('m4','akm')){
 $label="stock5080-final-$weapon";$log=Join-Path $stockOut "$weapon-load.log"
 $flags=if($weapon -eq 'akm'){' -StockAKM'}else{''}
 $stockArgs='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -RenderOffscreen -ResX=1600 -ResY=900 -ForceRes -unattended -nosplash -nosound -SkeletonStockAudit -StockLoad -StockRun={1} -ColdSteelProfile=StockAudit_stock5080-refined-v1_{2} -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60" -abslog="{3}"{4}' -f $stockRoot,$label,$weapon,$log,$flags
 Copy-Item -LiteralPath "$stockRoot/Binaries/Win64/UnrealEditor.modules" -Destination (Join-Path $stockOut "$weapon-modules.json")
 $stockProcess=Start-Process $stockUE -ArgumentList $stockArgs -WindowStyle Hidden -PassThru
 Write-Output "Started owned final stock audit $label PID=$($stockProcess.Id)"
 $deadline=[DateTime]::UtcNow.AddSeconds(600)
 while(!$stockProcess.WaitForExit(1000)){if([DateTime]::UtcNow -gt $deadline){throw "Owned audit timeout PID=$($stockProcess.Id)"}}
 $text=[IO.File]::ReadAllText($log)
 if($stockProcess.ExitCode -ne 0 -or $text -notmatch 'STOCK_AUDIT: COMPLETE checks=\d+ failures=0' -or $text -match 'STOCK_AUDIT: FAIL|Failed to compile Material'){throw "Final stock audit failed $label : $log"}
 Copy-Item -LiteralPath "$stockRoot/Saved/SkeletonStockAudit/$label" -Destination (Join-Path $stockOut "$weapon-load") -Recurse
 Write-Output "PASS $label"
}
