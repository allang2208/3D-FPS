param([ValidateRange(1,3600)][int]$QueueWaitSeconds=300, [switch]$ResumePartialAssets)
$ErrorActionPreference = 'Stop'
$leatherProject = 'D:/FPS3D/FPSGAME'
$leatherRoot = "$leatherProject/SourceAssets/BrownLeatherSet20261004"
$leatherAssetRoot = "$leatherProject/Content/Characters/ModularOutfit20260924/BrownLeatherSet20261004"
$leatherEngine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$leatherGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$leatherHeld = $false
try {
    try { $leatherHeld = $leatherGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) } catch [Threading.AbandonedMutexException] { $leatherHeld = $true }
    if (-not $leatherHeld) { throw 'The current UE authoring batch is still active; no commandlet started.' }
    if (Test-Path -LiteralPath $leatherAssetRoot) {
        if (-not $ResumePartialAssets) { throw 'Leather set packages already exist; resume the completed stage deliberately.' }
        $leatherEditor = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }
        if ($leatherEditor) { throw 'An editor is active; update existing set packages through its bridge.' }
    }
    & $leatherEngine "$leatherProject/FPSGAME.uproject" -run=pythonscript "-script=$leatherProject/Tools/BrownLeatherSet/save_assets.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$leatherRoot/save-assets.log" *> "$leatherRoot/save-assets-console.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Leather set asset creation failed; see save-assets.log.' }
    & py -3.11 "$leatherProject/Tools/BrownLeatherSet/publish_catalog.py"
    if ($LASTEXITCODE -ne 0) { throw 'Leather set publication failed.' }
    foreach ($leatherDefinition in @('ue_leather_boots','ue_leather_pants')) {
        & $leatherEngine "$leatherProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog "-Definition=$leatherDefinition" -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$leatherRoot/icon-$leatherDefinition.log" *> "$leatherRoot/icon-$leatherDefinition-console.txt"
        if ($LASTEXITCODE -ne 0) { throw "Leather equipment icon production failed: $leatherDefinition" }
        Copy-Item -LiteralPath "$leatherProject/Content/ColdSteelData/Icons/$leatherDefinition.png" -Destination "$leatherRoot/$leatherDefinition.png"
    }
    Write-Output 'BROWN_LEATHER_SET_BACKGROUND_COMPLETE'
} finally {
    if ($leatherHeld) { $leatherGate.ReleaseMutex() }
    $leatherGate.Dispose()
}
