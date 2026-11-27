$ErrorActionPreference = 'Stop'

# Guard: never run while UnrealEditor GUI is open
$ueGui = Get-Process -Name 'UnrealEditor' -ErrorAction SilentlyContinue
if ($ueGui) {
    throw "UnrealEditor GUI is still open (PID=$($ueGui[0].Id)). Close UE Editor first."
}

$UeCmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$BuildBat = 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$Project = 'D:/FPS3D/FPSGAME/FPSGAME.uproject'

$svchArt = 'F:/FPSGAMEData/ArtProduction/SVCHReplacement20261018/EquipLeftBolt-20261126'
$hpaArt = 'F:/FPSGAMEData/ArtProduction/HeartPiercingArrow/ColabImpactV2-20261126'
New-Item -ItemType Directory -Force -Path $svchArt, $hpaArt | Out-Null

# Wait if any background compiler/UE-Cmd is busy
while ($true) {
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('cl.exe', 'link.exe', 'UnrealBuildTool.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'D:[\/]FPS3D[\/]FPSGAME')
    })
    if (-not $busy.Count) { break }
    Write-Host "Waiting for busy process: $($busy[0].Name) PID=$($busy[0].ProcessId)"
    Start-Sleep -Seconds 3
}

Write-Host "=== STEP 1: INSTALL 5 SVCH LEFT-BOLT EQUIP PROFILES ==="
$svchLog = Join-Path $svchArt ('ue-install-equip-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$svchScript = 'D:/FPS3D/FPSGAME/SourceAssets/SVCHReplacement20261018/EquipLeftBolt20261126/install_equip_left_bolt.py'
& $UeCmd $Project -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$svchLog" -run=pythonscript "-script=$svchScript" *> ($svchLog + '.stdout.txt')
if ($LASTEXITCODE -ne 0) {
    Get-Content ($svchLog + '.stdout.txt') -Tail 30 -ErrorAction SilentlyContinue
    throw "SVCh profile install failed (exit=$LASTEXITCODE)"
}
Get-Content ($svchLog + '.stdout.txt') | Select-String 'SVCH_EQUIP_LEFT_BOLT'
Write-Host "SVCH_PROFILES_OK"

Write-Host "=== STEP 2: IMPORT HEART-PIERCING ARROW V1 AUDIO ==="
& 'D:\FPS3D\FPSGAME\Tools\AudioPipeline\run_ue_import.ps1' `
    -SpecPath (Join-Path $hpaArt 'import_spec.json') `
    -ReceiptPath (Join-Path $hpaArt 'audio_import_receipt.json')
if ($LASTEXITCODE -ne 0) { throw "HeartPiercingArrow audio import failed (exit=$LASTEXITCODE)" }
Copy-Item -Force 'D:\FPS3D\FPSGAME\Content\Skills\HeartPiercingArrow\Audio20261026\S_HeartPiercingArrow_Release.uasset' `
    (Join-Path $hpaArt 'PublishedUAssets\S_HeartPiercingArrow_Release.uasset')
Write-Host "HPA_AUDIO_OK"

Write-Host "=== STEP 3: INCREMENTAL BUILD FPSGAMEEditor Win64 Development ==="
$buildLog = Join-Path $svchArt 'FPSGAMEEditor-Build-20261126.log'
& $BuildBat FPSGAMEEditor Win64 Development $Project -WaitMutex -FromMsBuild *> $buildLog
$buildExit = $LASTEXITCODE
Write-Host "BUILD_EXIT=$buildExit"
Get-Content $buildLog -Tail 20
if ($buildExit -ne 0) { throw "FPSGAMEEditor build failed (exit=$buildExit)" }

Write-Host "=== STEP 4: VERIFY DLL & ASSET HASHES ==="
$dll = Get-Item 'D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME.dll'
Write-Host ("DLL: {0} | {1} bytes | {2}" -f $dll.FullName, $dll.Length, $dll.LastWriteTime.ToString('s'))
$verify = @(
    'D:\FPS3D\FPSGAME\Content\Weapons\SVCH\Replacement20261018\SightsR2\ElbowFit\DA_SVCH_ElbowFitGrip.uasset',
    'D:\FPS3D\FPSGAME\Content\Weapons\SVCH\Replacement20261018\ForegripFit20261019\DA_SVCH_Grip_angled.uasset',
    'D:\FPS3D\FPSGAME\Content\Weapons\SVCH\Replacement20261018\ForegripFit20261019\DA_SVCH_Grip_vertical.uasset',
    'D:\FPS3D\FPSGAME\Content\Weapons\SVCH\Replacement20261018\ForegripFit20261019\DA_SVCH_Grip_canted.uasset',
    'D:\FPS3D\FPSGAME\Content\Weapons\SVCH\Replacement20261018\ForegripFit20261019\DA_SVCH_Grip_prism.uasset',
    'D:\FPS3D\FPSGAME\Content\Skills\HeartPiercingArrow\Audio20261026\S_HeartPiercingArrow_Release.uasset'
)
foreach ($p in $verify) {
    $it = Get-Item $p
    $h = (Get-FileHash -Algorithm SHA256 $p).Hash.ToLower()
    Write-Host ("{0} | {1} | {2} | {3}" -f $it.Name, $it.Length, $it.LastWriteTime.ToString('s'), $h)
}
Write-Host "PUBLISH_BATCH_COMPLETE"
