$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromMinutes(40)) }
    catch [Threading.AbandonedMutexException] { $held=$true }
    if (-not $held) { throw 'Icon production queue timed out.' }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'An editor is open; production icon generation deferred.' }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=ColdSteelWeaponIconCatalog -Definition=ue_xuanchi_zhenyue -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/Icons/inventory-author.log" *> "$taskRoot/Icons/inventory-console.log"
    if ($LASTEXITCODE -ne 0) { throw 'Inventory icon production failed; see Icons/inventory-author.log.' }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/import_icons.py" -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/Icons/import-commandlet.log" *> "$taskRoot/Icons/import-console.log"
    if ($LASTEXITCODE -ne 0) { throw 'Icon asset save failed; see Icons/import-commandlet.log.' }
    Write-Output 'XUANCHI_INVENTORY_AND_PART_ICONS_SAVED'
} finally {
    if ($held) { $gate.ReleaseMutex() };$gate.Dispose()
}
