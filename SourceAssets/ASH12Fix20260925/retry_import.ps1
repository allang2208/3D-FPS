# Save the straight-arm ASH-12 reload clips as soon as the play session ends.
# The importer itself refuses to run during PIE, so this only retries the guard.
$ErrorActionPreference = 'Continue'
$root = 'D:\FPS3D\FPSGAME'
$log = 'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925\import_retry.log'
Remove-Item $log -ErrorAction SilentlyContinue
function Try-Import([string]$script, [string]$tag) {
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript $script 2>&1
    $text = ($out | Out-String)
    if ($text -match 'success=True') { "OK $tag" | Add-Content $log; return $true }
    if ($text -match 'Active play session') { "WAIT $tag (PIE active)" | Add-Content $log; return $false }
    "FAIL $tag" | Add-Content $log
    $text.Substring(0, [Math]::Min(400, $text.Length)) | Add-Content $log
    return $false
}
for ($i = 0; $i -lt 60; $i++) {
    $a = Try-Import "$root\SourceAssets\ASH12Fix20260925\import_ash12_fix.py" 'base'
    $b = Try-Import "$root\SourceAssets\ASH12Fix20260925\import_ash12_families.py" 'families'
    if ($a -and $b) { 'IMPORT_RETRY_DONE' | Add-Content $log; break }
    Start-Sleep -Seconds 30
}
'IMPORT_RETRY_END' | Add-Content $log
