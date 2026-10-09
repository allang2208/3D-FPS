$ErrorActionPreference = 'Stop'
$root = 'D:/FPS3D/FPSGAME'
$assetGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$assetHeld = $false
try {
    while (-not $assetHeld) {
        try { $assetHeld = $assetGate.WaitOne(30000) }
        catch [Threading.AbandonedMutexException] { $assetHeld = $true }
    }
    do {
        $assetBusy = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor.exe', 'UnrealEditor-Cmd.exe', 'cl.exe', 'link.exe')
        })
        if ($assetBusy.Count -gt 0) { Start-Sleep -Seconds 5 }
    } while ($assetBusy.Count -gt 0)
    & "$root/Tools/ModularOutfit/Run-Authoring.ps1" `
        -Script 'SourceAssets/BenelliM4Super9020261006/finish_fingerless_skin.py' `
        -Log 'SourceAssets/BenelliM4Super9020261006/import_fingerless.log'
} finally {
    if ($assetHeld) { $assetGate.ReleaseMutex() }
    $assetGate.Dispose()
}
