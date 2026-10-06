param([switch]$NewAssetsOnly, [switch]$IconsOnly)
$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskRoot = "$taskProject/SourceAssets/ChainmailPants20261004"
$taskEngine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    try { $taskHeld = $taskGate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    if (-not $taskHeld) { throw 'The current UE authoring batch is still active; no commandlet started.' }
    if (-not $IconsOnly) {
        $taskEditor = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }
        if ($taskEditor -and -not $NewAssetsOnly) { throw 'An editor is active; use the existing bridge for asset mutations.' }
        if ($NewAssetsOnly -and (Test-Path -LiteralPath "$taskProject/Content/Characters/ModularOutfit20260924/ChainmailPants20261004")) {
            throw 'The new asset root already exists; preserve it and use its owning editor or a closed-editor commandlet.'
        }
        & $taskEngine "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskProject/Tools/ChainmailPants/save_assets.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$taskRoot/save-assets.log" *> "$taskRoot/save-assets-console.txt"
        if ($LASTEXITCODE -ne 0) { throw 'Asset creation failed; see save-assets.log.' }
        & py -3.11 "$taskProject/Tools/ChainmailPants/publish_catalog.py"
        if ($LASTEXITCODE -ne 0) { throw 'Catalog publication failed.' }
    }
    # This is the required item icon production pass, not a gameplay render.
    & $taskEngine "$taskProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_chainmail_pants -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$taskRoot/icon-production.log" *> "$taskRoot/icon-production-console.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Item icon production failed; see icon-production.log.' }
    Copy-Item -LiteralPath "$taskProject/Content/ColdSteelData/Icons/ue_chainmail_pants.png" -Destination "$taskRoot/ue_chainmail_pants.png"
    Write-Output 'CHAINMAIL_PANTS_BACKGROUND_COMPLETE'
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
