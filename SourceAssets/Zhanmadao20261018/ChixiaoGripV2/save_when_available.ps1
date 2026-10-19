$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Animation save queue timed out'}
 $deadline=(Get-Date).AddMinutes(5)
 while(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue){
  if((Get-Date)-gt $deadline){throw 'An active commandlet still owns the project; preserved it'}
  Start-Sleep -Seconds 2
 }
 if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){
  for($pass=0;$pass-lt 3;$pass++){
   & py -3.11 -X utf8 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/ue_python_exec.py' --script (Join-Path $PSScriptRoot 'save_in_editor.py') --timeout 120 *> (Join-Path $PSScriptRoot "adaptive-editor-$pass.log")
   if($LASTEXITCODE-ne 0){throw 'Existing-editor animation save failed; see adaptive-editor log'}
   $state=Get-Content (Join-Path $PSScriptRoot 'editor-save-state.json') -Raw | ConvertFrom-Json
   if($state.state-eq 'saved'){break}
   if($state.state-ne 'pie_end_requested'){throw 'Unexpected save result'}
   Start-Sleep -Seconds 2
  }
  if($state.state-ne 'saved'){throw 'PIE has not finished releasing the animations'}
 } else {
  & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ("-script="+(Join-Path $PSScriptRoot 'install_grip.py')) -unattended -nosplash -NullRHI -NoSound -NoP4 -UTF8Output ("-abslog="+(Join-Path $PSScriptRoot 'install-commandlet.log')) *> (Join-Path $PSScriptRoot 'install-console.log')
  $result=$LASTEXITCODE
  @{exit_code=$result;finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 'commandlet-receipt.json') -Encoding UTF8
  if($result-ne 0){throw "Animation save failed ($result)"}
 }
 & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'finalize.py')
 if($LASTEXITCODE-ne 0){throw 'Delivery receipt is incomplete'}
 Write-Output 'CHIXIAO_GRIP_V2_INSTALLED'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}