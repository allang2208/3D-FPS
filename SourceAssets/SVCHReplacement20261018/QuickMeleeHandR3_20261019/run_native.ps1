param([string[]]$Modes=@('baseline','candidate'))
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 Write-Output 'Waiting for native hand-review window'
 try{$held=$gate.WaitOne([TimeSpan]::FromSeconds(1200))}catch [Threading.AbandonedMutexException]{$held=$true}
 if(!$held){throw 'Native hand-review window stayed busy'}
 if(!(Test-Path -LiteralPath "$PSScriptRoot/build_receipt.json")){throw 'Native hand-review build is not ready'}
 $ue='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
 foreach($mode in $Modes) {
  $args=@("$taskProject/FPSGAME.uproject",'-run=ShotgunAttachmentAudit','-SVCHReview','-SVCHHandOnly','-nullrhi','-nosound','-unattended','-nop4','-nosplash','-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0,fps.body.AsyncPreload 0',"-Output=$PSScriptRoot/native-$mode.json","-abslog=$PSScriptRoot/native-$mode.log")
  if($mode -eq 'candidate'){$args+="-Candidate=$PSScriptRoot/Profiles"}
  if($mode -eq 'saved-glove'){$args+='-SVCHBlueGlove'}
  & $ue @args *> "$PSScriptRoot/native-$mode-console.log"
  if($LASTEXITCODE -ne 0){throw "Native $mode hand capture failed"}
  $data=Get-Content -LiteralPath "$PSScriptRoot/native-$mode.json" -Raw | ConvertFrom-Json
  if(!$data.real_gunplay_graph -or $data.families.Count -ne 5){throw 'Incomplete native hand capture'}
  Write-Output "NATIVE_HAND_CAPTURE_COMPLETE $mode"
 }
 $savedMode=@($Modes|Where-Object {$_ -like 'saved*'}).Count -gt 0
 $receipt=if($savedMode){'native-saved-receipt.json'}else{'native-receipt.json'}
 @{complete=$true;candidate_assets_saved=$savedMode;modes=$Modes;frames_per_family=110;families=5;interactive_game_started=$false}|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/$receipt" -Encoding utf8
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
