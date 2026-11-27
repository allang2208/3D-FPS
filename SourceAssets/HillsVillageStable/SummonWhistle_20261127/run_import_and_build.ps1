$ErrorActionPreference = 'Stop'

$ueGui = Get-Process -Name 'UnrealEditor' -ErrorAction SilentlyContinue
if ($ueGui) { throw "UnrealEditor GUI is still open (PID=$($ueGui[0].Id)). Close UE Editor first." }

$artDir = 'F:\FPSGAMEData\ArtProduction\HillsVillageStable\SummonWhistle-20261127'
$specPath = Join-Path $artDir 'import_spec.json'
$receiptPath = Join-Path $artDir 'audio_import_receipt.json'
$pubDir = Join-Path $artDir 'PublishedUAssets'
New-Item -ItemType Directory -Force -Path $pubDir | Out-Null

Write-Host "=== STEP 1: HEADLESS UE5 AUDIO IMPORT (3 SoundWaves + ATT + CON) ==="
& 'D:\FPS3D\FPSGAME\Tools\AudioPipeline\run_ue_import.ps1' -SpecPath $specPath -ReceiptPath $receiptPath
if ($LASTEXITCODE -ne 0) { throw "Audio import failed (exit=$LASTEXITCODE)" }

$assets = @(
  'D:\FPS3D\FPSGAME\Content\WorldGeneration\TemperateHills\VillageStable\Horses\Audio\SW_Horse_SummonWhistle_01.uasset',
  'D:\FPS3D\FPSGAME\Content\WorldGeneration\TemperateHills\VillageStable\Horses\Audio\SW_Horse_SummonWhistle_02.uasset',
  'D:\FPS3D\FPSGAME\Content\WorldGeneration\TemperateHills\VillageStable\Horses\Audio\SW_Horse_SummonWhistle_03.uasset',
  'D:\FPS3D\FPSGAME\Content\WorldGeneration\TemperateHills\VillageStable\Horses\Audio\ATT_HorseSummonWhistle.uasset',
  'D:\FPS3D\FPSGAME\Content\WorldGeneration\TemperateHills\VillageStable\Horses\Audio\CON_HorseSummonWhistle.uasset'
)
foreach ($a in $assets) {
  if (-not (Test-Path $a)) { throw "Missing imported asset: $a" }
  Copy-Item -Force $a (Join-Path $pubDir (Split-Path -Leaf $a))
}
Write-Host "IMPORT_AND_COPY_OK"

Write-Host "=== STEP 2: INCREMENTAL BUILD FPSGAMEEditor Win64 Development ==="
$buildLog = Join-Path $artDir 'FPSGAMEEditor-Build-20261127.log'
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development D:/FPS3D/FPSGAME/FPSGAME.uproject -WaitMutex -FromMsBuild *> $buildLog
$buildExit = $LASTEXITCODE
Write-Host "BUILD_EXIT=$buildExit"
Get-Content $buildLog -Tail 25
if ($buildExit -ne 0) { throw "FPSGAMEEditor build failed (exit=$buildExit)" }

Write-Host "=== STEP 3: VERIFY HASHES & DLL ==="
$dll = Get-Item 'D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME.dll'
Write-Host ("DLL: {0} | {1} bytes | {2}" -f $dll.Name, $dll.Length, $dll.LastWriteTime.ToString('s'))
foreach ($a in $assets) {
  $it = Get-Item $a
  $h = (Get-FileHash -Algorithm SHA256 $a).Hash.ToLower()
  Write-Host ("{0} | {1} | {2} | {3}" -f $it.Name, $it.Length, $it.LastWriteTime.ToString('s'), $h)
}
Write-Host "HORSE_WHISTLE_ALL_DONE"
