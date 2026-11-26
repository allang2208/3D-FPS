param([string]$CaptureLabel='Before',[switch]$HideRobeHood,[switch]$Before,[switch]$Unlit,[switch]$NoHair,[switch]$OriginalFace,[switch]$Refined,[switch]$NoShadows,[switch]$ExportNativeHair,[switch]$RuntimePose,[switch]$AllowGameBuild,[switch]$ReferenceHair)
$Label=if($Before){'quality-before'}elseif($Unlit){'quality-unlit'}elseif($NoHair){'quality-faceonly'}else{'quality-after'}
$ErrorActionPreference='Stop'
$nunRoot='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HeadQualityR2'
if($OriginalFace){$nunRoot='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/OriginalMeshyFaceR3'}
if($Refined -or $ExportNativeHair){$nunRoot='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/RefinementR4'}
if($ReferenceHair){$nunRoot='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HairReferenceR5'}
if($NoShadows){$Label='quality-no-shadows'}
if($ExportNativeHair){$Label='native-hair-export'}
if($RuntimePose){$Label='quality-runtime'}
$nunRoot='D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/IdleCrossedR4/Review'
$Label=$CaptureLabel
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
 $nunArgs=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"','/Engine/Maps/Entry','-run=ChapelNunQuality','-unattended','-nop4','-nosplash','-nosound','-AllowCommandletRendering','-RenderOffscreen','-ini:Engine:[SystemSettings]:r.HairStrands.SwapType=0','-Multiprocess','-AssetGatherAll=false','-asyncskinnedassetcompilation=0','-asyncstaticmeshcompilation=0','-asynctexturecompilation=0',"-abslog=$nunRoot/Logs/$Label-engine.log")
 $nunArgs+=@('-OriginalFace','-Refined','-ReferenceHair','-RuntimePose','-CrossedIdleReview',"-CaptureOut=$nunRoot/$CaptureLabel")
if($HideRobeHood){$nunArgs+='-HideRobeHood'}
if($Before){$nunArgs+= '-Before'}
 if($OriginalFace){$nunArgs+= '-OriginalFace'}
 if($Refined){$nunArgs+= @('-OriginalFace','-Refined')}
 if($ReferenceHair){$nunArgs+= '-ReferenceHair'}
 if($NoShadows){$nunArgs+= '-NoShadows'}
 if($ExportNativeHair){$nunArgs+= '-ExportNativeHair'}
 if($RuntimePose){$nunArgs+= '-RuntimePose'}
 if($Unlit){$nunArgs+= '-Unlit'}
 if($NoHair){$nunArgs+= '-ini:Engine:[SystemSettings]:r.HairStrands.Strands=0'}
 $nunProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $nunArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput "$nunRoot/Logs/$Label-stdout.log" -RedirectStandardError "$nunRoot/Logs/$Label-stderr.log"
 $nunHandle=$nunProcess.Handle
 $nunProcess.PriorityClass='Normal'
 $nunProcess.WaitForExit()
 $nunCode=$nunProcess.ExitCode
 Write-Output "NUN_AUTHOR_EXIT $nunCode"
 Get-Content -LiteralPath "$nunRoot/Logs/$Label-stdout.log" -Tail 8
 exit $nunCode
} finally {if($nunHeld){$nunGate.ReleaseMutex()};$nunGate.Dispose()}
