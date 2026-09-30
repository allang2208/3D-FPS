param([int]$Minutes = 60)
# Read-only collection that adapts to whoever holds the project: headless commandlet when no
# FPSGAME editor/commandlet runs, short bridge batches into a running FPSGAME editor (never
# during PIE), otherwise wait. FPSGAME-mp is a separate project and is ignored.
$root = $PSScriptRoot
$t0 = Get-Date
while (((Get-Date) - $t0).TotalMinutes -lt $Minutes) {
    $procs = Get-CimInstance Win32_Process -Filter "name='UnrealEditor.exe' OR name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -notmatch 'FPSGAME-mp' }
    $editor = $procs | Where-Object { $_.Name -eq 'UnrealEditor.exe' }
    $cmdlet = $procs | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' }
    if (-not $procs) {
        $o = powershell -NoProfile -ExecutionPolicy Bypass -File "$root\run_headless.ps1" -Script collect.py -WaitMinutes 5 2>&1 | Out-String
        Write-Output ("headless: " + ($o -replace '\s+', ' ').Trim())
        $log = Get-ChildItem $root -Filter 'commandlet-*.log' | Sort-Object LastWriteTime | Select-Object -Last 1
        if ($log -and (Select-String -Path $log.FullName -Pattern 'GRIPLAYER56_COMPLETE' -Quiet)) { Write-Output 'GRIPLAYER56_COMPLETE (headless)'; exit 0 }
        Start-Sleep 10; continue
    }
    if ($editor -and -not $cmdlet) {
        $o = powershell -NoProfile -ExecutionPolicy Bypass -File "$root\..\..\..\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript "$root\collect.py" -QueueWaitSeconds 300 2>&1 | Out-String
        $m = [regex]::Matches($o, 'GRIPLAYER56_(COMPLETE|PARTIAL|PIE)[^\r\n]{0,80}')
        if ($m.Count) { Write-Output ("bridge: " + $m[$m.Count - 1].Value) } else { Write-Output 'bridge: no editor node yet' }
        if ($o -match 'GRIPLAYER56_COMPLETE') { exit 0 }
        if ($o -match 'GRIPLAYER56_PARTIAL') { Start-Sleep 2 } else { Start-Sleep 30 }
        continue
    }
    Start-Sleep 20
}
Write-Output 'GRIPLAYER56 collect timed out'
exit 1
