$ErrorActionPreference = 'Stop'
$root = 'D:/FPS3D/FPSGAME'
$output = "$root/SourceAssets/BenelliM4Super9020261006"
$batchGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$batchHeld = $false
try {
    while (-not $batchHeld) {
        try { $batchHeld = $batchGate.WaitOne(30000) }
        catch [Threading.AbandonedMutexException] { $batchHeld = $true }
    }
    Write-Output 'Batch lock acquired; waiting for existing authoring and compilation processes.'
    do {
        $activeJobs = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor.exe', 'UnrealEditor-Cmd.exe', 'cl.exe', 'link.exe')
        })
        if ($activeJobs.Count -gt 0) { Start-Sleep -Seconds 5 }
    } while ($activeJobs.Count -gt 0)

    Write-Output 'Starting Super90 editor module build.'
    & "$root/Tools/Build/Build-Editor.ps1" *> "$output/build_editor.log"
    Write-Output 'Editor build completed; saving the fingerless glove skin companion.'
    & "$root/Tools/ModularOutfit/Run-Authoring.ps1" `
        -Script 'SourceAssets/BenelliM4Super9020261006/finish_fingerless_skin.py' `
        -Log 'SourceAssets/BenelliM4Super9020261006/import_fingerless.log' `
        *> "$output/import_fingerless_background03.log"
    Write-Output 'SUPER90_BACKGROUND_FINISH_COMPLETE'
} finally {
    if ($batchHeld) { $batchGate.ReleaseMutex() }
    $batchGate.Dispose()
}
