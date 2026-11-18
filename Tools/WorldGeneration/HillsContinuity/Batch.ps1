param([string]$Attempt='udp04',[string]$Batch='repair-batch')
$ErrorActionPreference='Stop'
$directory="D:/FPS3D/FPSGAME/Saved/HillsContinuity20261118/$Batch"
New-Item -ItemType Directory -Force -Path $directory|Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false;$serial=0
try {
 Write-Output 'Waiting for the existing UE batch gate.'
 try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
 while($true){
  if($Attempt -notmatch '^udp[0-9]+$'){throw 'Invalid isolated attempt name'}
  @{state='running';attempt=$Attempt}|ConvertTo-Json|Set-Content -LiteralPath "$directory/state.json"
  try{& "$PSScriptRoot/Run.ps1" -Attempt $Attempt}catch{Write-Output $_.Exception.Message}
  $receipt="D:/FPS3D/FPSGAME/Saved/HillsContinuity20261118/$Attempt/summary.json"
  if((Test-Path -LiteralPath $receipt) -and (Get-Content -LiteralPath $receipt -Raw|ConvertFrom-Json).passed){break}
  # Keep this same work batch locked while its own failed case is diagnosed.
  # The control file is private to this runner; it sends no coordination messages.
  @{state='awaiting_retry';attempt=$Attempt;serial=$serial}|ConvertTo-Json|Set-Content -LiteralPath "$directory/state.json"
  Write-Output "HILLS_CONTINUITY_AWAIT_RETRY attempt=$Attempt serial=$serial"
  $deadline=[DateTime]::UtcNow.AddMinutes(20)
  while($true){
   if([DateTime]::UtcNow -gt $deadline){throw 'Own-batch retry window expired'}
   if(Test-Path -LiteralPath "$directory/action.json"){
    $action=Get-Content -LiteralPath "$directory/action.json" -Raw|ConvertFrom-Json
    if($action.serial -gt $serial){$serial=$action.serial;if($action.action -eq 'stop'){exit};$Attempt=$action.attempt;break}
   };Start-Sleep -Seconds 2
  }
 }
 @{state='complete';attempt=$Attempt}|ConvertTo-Json|Set-Content -LiteralPath "$directory/state.json"
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
