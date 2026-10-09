$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    for ($attempt = 0; $attempt -lt 20 -and -not $held; ++$attempt) {
        try { $held = $gate.WaitOne(30000) } catch [Threading.AbandonedMutexException] { $held = $true }
        if (-not $held) { continue }
        $processes = @(Get-CimInstance Win32_Process)
        $editor = @($processes | Where-Object {
            $_.Name -eq 'UnrealEditor.exe' -and
            ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
        })
        if ($editor.Count -gt 0) { throw 'FPSGAME editor is running. Preserve it; the source fix is saved but its native build must wait.' }
        $busy = @($processes | Where-Object {
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and
                ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe'
        })
        if ($busy.Count -gt 0) {
            $gate.ReleaseMutex(); $held = $false
            Write-Output 'An existing authoring/build batch is active; waiting without starting another process.'
            Start-Sleep -Seconds 30
        }
    }
    if (-not $held) { throw 'Existing UE batch remains busy. Source is saved; no competing build was started.' }
    & "$projectRoot/Tools/Build/Build-Editor.ps1"
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
