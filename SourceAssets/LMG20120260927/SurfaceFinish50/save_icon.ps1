$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskIcon="$taskRoot/Content/ColdSteelData/Icons/ue_lmg201.png"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $taskHeld){throw 'Shared asset bridge busy; catalog production not started'}
    # Catalog production only reads saved meshes/materials and writes this
    # weapon's PNG. It does not save packages loaded by an existing editor.
    $taskReceipt=Get-Content -LiteralPath "$PSScriptRoot/delivery.json" -Raw | ConvertFrom-Json
    if($taskReceipt.status -ne 'current_surface_finish50_saved'){throw 'Current F50 assets must be saved before icon production'}
    $taskBackup="$PSScriptRoot/Before/ue_lmg201.png"
    if(-not (Test-Path -LiteralPath $taskBackup)){Copy-Item -LiteralPath $taskIcon -Destination $taskBackup}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" '-run=ColdSteelWeaponIconCatalog' '-Definition=ue_lmg201' '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoTextureStreaming' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$PSScriptRoot/catalog.log" *> "$PSScriptRoot/catalog_console.log"
    if($LASTEXITCODE -ne 0){throw "Catalog production failed: $LASTEXITCODE"}
    $taskReceipt.icon_pending=$false
    $taskReceipt | Add-Member -MemberType NoteProperty -Name icon -Value ([ordered]@{file=$taskIcon;sha256=(Get-FileHash -LiteralPath $taskIcon -Algorithm SHA256).Hash;grid=@(5,2);canvas=@(800,320);silhouetteFill=0.91;productionOnly=$true}) -Force
    $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$PSScriptRoot/delivery.json" -Encoding utf8
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
