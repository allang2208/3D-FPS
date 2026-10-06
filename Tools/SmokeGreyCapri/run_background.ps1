param([ValidateSet('extract','save','repair','icon')][string]$Stage,[int]$QueueWaitSeconds=300)
$ErrorActionPreference='Stop'
$capriProject='D:/FPS3D/FPSGAME'
$capriRoot="$capriProject/SourceAssets/SmokeGreyCapri20261004"
$capriEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$capriGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$capriHeld=$false
try {
    try { $capriHeld=$capriGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) } catch [Threading.AbandonedMutexException] { $capriHeld=$true }
    if (-not $capriHeld) { throw 'An existing UE authoring batch is still running.' }
    if ($Stage -eq 'icon') {
        & $capriEngine "$capriProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_smoke_grey_capri -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$capriRoot/icon-production.log" *> "$capriRoot/icon-production-console.txt"
        if ($LASTEXITCODE -ne 0) { throw 'Capri icon production failed.' }
        Copy-Item -LiteralPath "$capriProject/Content/ColdSteelData/Icons/ue_smoke_grey_capri.png" -Destination "$capriRoot/ue_smoke_grey_capri.png"
    } else {
        $capriScript=if ($Stage -eq 'extract') { 'extract_calf.py' } elseif ($Stage -eq 'repair') { 'save_crotch_repair.py' } else { 'save_assets.py' }
        if ($Stage -in @('save','repair') -and (Test-Path -LiteralPath "$capriProject/Content/Characters/ModularOutfit20260924/SmokeGreyCapri20261004")) {
            $capriEditor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }
            if ($capriEditor) { throw 'Existing capri packages require the active editor bridge.' }
        }
        & $capriEngine "$capriProject/FPSGAME.uproject" -run=pythonscript "-script=$capriProject/Tools/SmokeGreyCapri/$capriScript" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$capriRoot/$Stage-assets.log" *> "$capriRoot/$Stage-assets-console.txt"
        if ($LASTEXITCODE -ne 0) { throw "Capri $Stage failed; see $Stage-assets.log." }
    }
    Write-Output "CAPRI_BACKGROUND_COMPLETE $Stage"
} finally {
    if ($capriHeld) { $capriGate.ReleaseMutex() }
    $capriGate.Dispose()
}
