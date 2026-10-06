param([switch]$UpdateOwnedAssets, [ValidateRange(1,3600)][int]$QueueWaitSeconds=60)
$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskRoot = "$taskProject/SourceAssets/ChainmailPants20261004/ArmorRefineV2"
$taskAssetRoot = "$taskProject/Content/Characters/ModularOutfit20260924/ChainmailPants20261004/ArmorRefineV2"
$taskEngine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    try { $taskHeld = $taskGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    if (-not $taskHeld) { throw 'The current UE authoring batch is still active; no commandlet started.' }
    # V1 may be loaded in another editor; this batch only creates new packages.
    if (Test-Path -LiteralPath $taskAssetRoot) {
        if (-not $UpdateOwnedAssets) { throw 'V2 packages already exist; preserve them and use their owning editor for updates.' }
        $taskEditor = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }
        if ($taskEditor) { throw 'An editor is active; update the existing V2 assets through its bridge.' }
    }
    & $taskEngine "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskProject/Tools/ChainmailPants/save_refined_assets.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$taskRoot/save-assets.log" *> "$taskRoot/save-assets-console.txt"
    if ($LASTEXITCODE -ne 0) { throw 'V2 asset creation failed; see save-assets.log.' }
    & py -3.11 "$taskProject/Tools/ChainmailPants/publish_refined_armor.py"
    if ($LASTEXITCODE -ne 0) { throw 'V2 publication failed.' }
    $taskEditor = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }
    if ($taskEditor) { throw 'V2 saved. Existing inventory mesh paths still need the current editor bridge; see update_saved_instance_meshes.py.' }
    $taskBackup = "$taskRoot/PreviousStaticPackages"
    New-Item -ItemType Directory -Path $taskBackup -Force | Out-Null
    foreach ($taskRelative in @('Icons/SM_ChainmailPants_Display.uasset','Pickups/SM_ChainmailPants.uasset')) {
        $taskInput = "$taskProject/Content/Characters/ModularOutfit20260924/ChainmailPants20261004/$taskRelative"
        $taskCopy = Join-Path $taskBackup ([IO.Path]::GetFileName($taskRelative))
        if (-not (Test-Path -LiteralPath $taskCopy)) { Copy-Item -LiteralPath $taskInput -Destination $taskCopy }
    }
    & $taskEngine "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskProject/Tools/ChainmailPants/update_saved_instance_meshes.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$taskRoot/existing-instance-assets.log" *> "$taskRoot/existing-instance-assets-console.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Existing inventory mesh update failed; see existing-instance-assets.log.' }
    & $taskEngine "$taskProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_chainmail_pants -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$taskRoot/icon-production.log" *> "$taskRoot/icon-production-console.txt"
    if ($LASTEXITCODE -ne 0) { throw 'V2 item icon production failed; see icon-production.log.' }
    Copy-Item -LiteralPath "$taskProject/Content/ColdSteelData/Icons/ue_chainmail_pants.png" -Destination "$taskRoot/ue_chainmail_pants.png"
    Write-Output 'CHAINMAIL_ARMOR_V2_BACKGROUND_COMPLETE'
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
