$ErrorActionPreference = 'Stop'
$dungeonRoot = Split-Path -Parent $PSScriptRoot
$receiptName = 'bridge-install-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.txt'
$receiptPath = Join-Path (Join-Path $dungeonRoot 'Receipts') $receiptName
& 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' `
    -PythonScript (Join-Path $PSScriptRoot 'install_v2.py') `
    -OutputFile $receiptPath -MaxOutputChars 5000 -QueueWaitSeconds 180
exit $LASTEXITCODE
