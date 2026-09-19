param([string]$RunId=('stock-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$stockRoot='D:/FPS3D/FPSGAME'
$stockUE='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
if($RunId -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Simple unique label required'}
$stockOut=Join-Path $PSScriptRoot $RunId
if(Test-Path -LiteralPath $stockOut){throw 'Output exists'}
New-Item -ItemType Directory -Path $stockOut | Out-Null
foreach($weapon in @('m4','akm')){
 foreach($phase in @('write','load')){
  $label="$RunId-$weapon-$phase";$log=Join-Path $stockOut "$weapon-$phase.log"
  $flags=if($weapon -eq 'akm'){' -StockAKM'}else{''}
  if($phase -eq 'load'){$flags+=' -StockLoad'}
  $stockArgs='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -RenderOffscreen -ResX=1600 -ResY=900 -ForceRes -unattended -nosplash -nosound -SkeletonStockAudit -StockRun={1} -ColdSteelProfile=StockAudit_{2}_{3} -ExecCmds="DisableAllScreenMessages,t.MaxFPS 60" -abslog="{4}"{5}' -f $stockRoot,$label,$RunId,$weapon,$log,$flags
  $stockProcess=Start-Process $stockUE -ArgumentList $stockArgs -WindowStyle Hidden -PassThru
  Write-Output "Started owned stock audit $label PID=$($stockProcess.Id)"
  $deadline=[DateTime]::UtcNow.AddSeconds(180)
  while(!$stockProcess.WaitForExit(1000)){if([DateTime]::UtcNow -gt $deadline){throw "Owned audit timeout PID=$($stockProcess.Id)"}}
  $text=[IO.File]::ReadAllText($log)
  if($stockProcess.ExitCode -ne 0 -or $text -notmatch 'STOCK_AUDIT: COMPLETE checks=\d+ failures=0' -or $text -match 'STOCK_AUDIT: FAIL'){throw "Stock audit failed $label : $log"}
  Copy-Item -LiteralPath "$stockRoot/Saved/SkeletonStockAudit/$label" -Destination (Join-Path $stockOut "$weapon-$phase") -Recurse
  Write-Output "PASS $label"
 }
}
