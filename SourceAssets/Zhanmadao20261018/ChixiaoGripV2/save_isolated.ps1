$ErrorActionPreference='Stop'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $PSScriptRoot 'AssetHost/AssetHost.uproject') -run=pythonscript ("-script="+(Join-Path $PSScriptRoot 'install_grip.py')) -unattended -nosplash -NullRHI -NoSound -NoP4 -UTF8Output ("-abslog="+(Join-Path $PSScriptRoot 'isolated-save.log')) *> (Join-Path $PSScriptRoot 'isolated-save-console.log')
if($LASTEXITCODE-ne 0){throw 'Isolated hand animation save failed'}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Publication queue timed out'}
 $deadline=(Get-Date).AddMinutes(5)
 while(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue){if((Get-Date)-gt $deadline){throw 'An active commandlet owns the project'};Start-Sleep -Seconds 2}
 if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){
  for($pass=0;$pass-lt 3;$pass++){
   & py -3.11 -X utf8 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/ue_python_exec.py' --script (Join-Path $PSScriptRoot 'save_in_editor.py') --timeout 120 *> (Join-Path $PSScriptRoot "isolated-editor-$pass.log")
   if($LASTEXITCODE-ne 0){throw 'Existing-editor animation save failed'}
   $state=Get-Content (Join-Path $PSScriptRoot 'editor-save-state.json') -Raw | ConvertFrom-Json
   if($state.state-eq 'saved'){break}
   Start-Sleep -Seconds 2
  }
  if($state.state-ne 'saved'){throw 'PIE still owns animations'}
 } else {
  & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'publish_isolated.py')
  if($LASTEXITCODE-ne 0){throw 'Animation publication failed'}
 }
 & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'finalize.py')
 if($LASTEXITCODE-ne 0){throw 'Delivery receipt incomplete'}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}