param()
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskFolder="$taskRoot/SourceAssets/LMG20120260927/InventoryIcon48"
$taskIcon="$taskRoot/Content/ColdSteelData/Icons/ue_lmg201.png"
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    $taskHeld=$taskMutex.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $taskHeld){throw 'Shared asset bridge busy; catalog production was not started'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing UE process retained; catalog production was not started'}
    $taskBackup="$taskFolder/Before/ue_lmg201.png"
    if(-not (Test-Path -LiteralPath $taskBackup)) {
        New-Item -ItemType Directory -Path "$taskFolder/Before" -Force | Out-Null
        Copy-Item -LiteralPath $taskIcon -Destination $taskBackup
        [ordered]@{file=$taskIcon;sha256=(Get-FileHash -LiteralPath $taskIcon -Algorithm SHA256).Hash;lastWriteTime=(Get-Item -LiteralPath $taskIcon).LastWriteTime.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$taskFolder/before.json" -Encoding utf8
    }
    # This offline production process has no streaming-world tick. Load full
    # texture data here; do not change the game's streaming settings or budget.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" '-run=ColdSteelWeaponIconCatalog' '-Definition=ue_lmg201' '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoTextureStreaming' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$taskFolder/catalog_fullmips.log" *> "$taskFolder/catalog_fullmips_console.log"
    $taskExit=$LASTEXITCODE
    if($taskExit -ne 0){throw "Catalog production failed with exit code $taskExit; see catalog.log"}
    [ordered]@{status='catalog_png_saved';file=$taskIcon;sha256=(Get-FileHash -LiteralPath $taskIcon -Algorithm SHA256).Hash;definition='ue_lmg201';grid=@(5,2);canvas=@(800,320);silhouetteFill=0.91;palette='Current weapon materials; no modification-icon grayscale conversion';runtimeAssembly='Installed recipe via SetGunsmithMagazineAttachment; current DrumJoint47 mesh at Drum46 asset path';runtimeTested=$false;acceptanceRendered=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$taskFolder/delivery.json" -Encoding utf8
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
