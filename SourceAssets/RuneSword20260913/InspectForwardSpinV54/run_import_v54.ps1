$script = Join-Path $PSScriptRoot 'import_inspect_v54.py'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$out = Join-Path $PSScriptRoot ("import_v54." + $stamp + ".bridge.txt")
& 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $script -QueueWaitSeconds 60 -OutputFile $out -MaxOutputChars 3000
exit $LASTEXITCODE
