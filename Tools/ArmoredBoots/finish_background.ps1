param([ValidateRange(1,3600)][int]$QueueWaitSeconds=300, [switch]$ResumePartialAssets)
$ErrorActionPreference = 'Stop'
$bootProject = 'D:/FPS3D/FPSGAME'
$bootRoot = "$bootProject/SourceAssets/ArmoredBoots20261004"
$bootAssetRoot = "$bootProject/Content/Characters/ModularOutfit20260924/ArmoredBoots20261004"
$bootEngine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$bootGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$bootHeld = $false
try {
    try { $bootHeld = $bootGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) } catch [Threading.AbandonedMutexException] { $bootHeld = $true }
    if (-not $bootHeld) { throw 'The current UE authoring batch is still active; no commandlet started.' }
    if (Test-Path -LiteralPath $bootAssetRoot) {
        if (-not $ResumePartialAssets) { throw 'Armored boot packages already exist; resume from the saved stage in their owning editor or background window.' }
        $bootEditor = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }
        if ($bootEditor) { throw 'An editor is active; resume these packages using its bridge.' }
    }
    & $bootEngine "$bootProject/FPSGAME.uproject" -run=pythonscript "-script=$bootProject/Tools/ArmoredBoots/save_assets.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$bootRoot/save-assets.log" *> "$bootRoot/save-assets-console.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Armored boot asset creation failed; see save-assets.log.' }
    & py -3.11 "$bootProject/Tools/ArmoredBoots/publish_catalog.py"
    if ($LASTEXITCODE -ne 0) { throw 'Armored boot catalog publication failed.' }
    & $bootEngine "$bootProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_armored_boots -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$bootRoot/icon-production.log" *> "$bootRoot/icon-production-console.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Armored boot icon production failed; see icon-production.log.' }
    Copy-Item -LiteralPath "$bootProject/Content/ColdSteelData/Icons/ue_armored_boots.png" -Destination "$bootRoot/ue_armored_boots.png"
    Write-Output 'ARMORED_BOOTS_BACKGROUND_COMPLETE'
} finally {
    if ($bootHeld) { $bootGate.ReleaseMutex() }
    $bootGate.Dispose()
}
