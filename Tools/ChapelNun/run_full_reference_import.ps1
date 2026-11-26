param([Parameter(Mandatory=$true)][string]$Script,[string]$Label='author',[switch]$AllowGameBuild,[string]$NunHairRevision='')
$ErrorActionPreference='Stop'
$nunRoot='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/ProductionR1'
$nunGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$nunHeld=$false
try {
 try {$nunHeld=$nunGate.WaitOne()} catch [Threading.AbandonedMutexException] {$nunHeld=$true}
 while($true) {
  $nunBusy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    $nunBusy=@($nunBusy | Where-Object { $_.Name -notlike 'UnrealEditor*' -or $_.CommandLine -notmatch '\.uproject' -or $_.CommandLine.Replace('\','/').Contains('D:/FPS3D/FPSGAME/FPSGAME.uproject') })
    if($AllowGameBuild){$nunBusy=@($nunBusy | Where-Object { $_.CommandLine -notmatch 'UnrealBuildTool[^\r\n]*\sFPSGAME\s+Win64\s+Development\s' })}
if(-not $nunBusy.Count){break}
  Write-Output 'Waiting for the existing engine/build process.'
  try {Wait-Process -Id $nunBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $nunBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
 }

 $nunGrooms=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME/Content/Characters/ChapelNun20261115/HairReferenceR5/Grooms')
 $nunBackup=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairFullReferenceR8/Before/Grooms')
 if(Test-Path -LiteralPath $nunBackup){throw 'Fresh import backup already exists; do not overwrite it.'}
 New-Item -ItemType Directory -Path $nunBackup | Out-Null
 $nunFiles=@('Nun_LowBun_Core_R5.uasset','Nun_LowBun_Core_R5_Binding.uasset','Nun_LowBun_Loose_R5.uasset','Nun_LowBun_Loose_R5_Binding.uasset')
 foreach($nunFile in $nunFiles){
  $nunTarget=[IO.Path]::GetFullPath((Join-Path $nunGrooms $nunFile))
  if([IO.Path]::GetDirectoryName($nunTarget) -ne $nunGrooms){throw 'Unexpected groom path'}
  Copy-Item -LiteralPath $nunTarget -Destination (Join-Path $nunBackup $nunFile)
  if((Get-FileHash -LiteralPath $nunTarget).Hash -ne (Get-FileHash -LiteralPath (Join-Path $nunBackup $nunFile)).Hash){throw 'Backup mismatch'}
 }
 $nunReceipt='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairReferenceR5/saved_assets.json'
 Copy-Item -LiteralPath $nunReceipt -Destination (Join-Path $nunBackup 'saved_assets.json')
 foreach($nunFile in $nunFiles){Remove-Item -LiteralPath (Join-Path $nunGrooms $nunFile)}
 $nunState=Get-Content -LiteralPath $nunReceipt -Raw | ConvertFrom-Json
 $nunState.assets=[pscustomobject]@{};$nunState.source_hashes=[pscustomobject]@{};$nunState.completed=$false
 $nunState | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $nunReceipt -Encoding UTF8
 Write-Output 'Backed up four owned packages and prepared fresh groom import.'

 $nunSource='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairFullReferenceR8/Authored'
 $nunActiveSource='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairReferenceR5/Authored'
 $nunSourceBackup='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairFullReferenceR8/Before/Source'
 New-Item -ItemType Directory -Path $nunSourceBackup | Out-Null
 foreach($nunSourceFile in @('Nun_LowBun_Core_R5.abc','Nun_LowBun_Loose_R5.abc','Nun_LowBun_Core_R5_rootuv.bin','Nun_LowBun_Loose_R5_rootuv.bin','Nun_LowBun_Core_R5_points.npy','Nun_LowBun_Loose_R5_points.npy')){
  Copy-Item -LiteralPath (Join-Path $nunActiveSource $nunSourceFile) -Destination (Join-Path $nunSourceBackup $nunSourceFile)
  Copy-Item -LiteralPath (Join-Path $nunSource $nunSourceFile) -Destination (Join-Path $nunActiveSource $nunSourceFile) -Force
 }
 Copy-Item -LiteralPath 'D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairReferenceR5/authoring.json' -Destination (Join-Path $nunSourceBackup 'authoring.json')
 Copy-Item -LiteralPath 'D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairFullReferenceR8/authoring.json' -Destination 'D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairReferenceR5/authoring.json' -Force
 $nunArgs=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"','/Engine/Maps/Entry','-run=pythonscript',"-script=$Script",'-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-AssetGatherAll=false','-asyncskinnedassetcompilation=0','-asyncstaticmeshcompilation=0','-asynctexturecompilation=0',"-abslog=$nunRoot/Logs/$Label-engine.log")
 if($NunHairRevision){$nunArgs+="-NunHairRevision=$NunHairRevision"}
 $nunProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $nunArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput "$nunRoot/Logs/$Label-stdout.log" -RedirectStandardError "$nunRoot/Logs/$Label-stderr.log"
 $nunHandle=$nunProcess.Handle
 $nunProcess.PriorityClass='Normal'
 $nunProcess.WaitForExit()
 $nunCode=$nunProcess.ExitCode
 Write-Output "NUN_AUTHOR_EXIT $nunCode"
 Get-Content -LiteralPath "$nunRoot/Logs/$Label-stdout.log" -Tail 8
 exit $nunCode
} finally {if($nunHeld){$nunGate.ReleaseMutex()};$nunGate.Dispose()}
