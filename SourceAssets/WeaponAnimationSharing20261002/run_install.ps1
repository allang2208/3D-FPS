$ErrorActionPreference = 'Stop'
& py -3.11 (Join-Path $PSScriptRoot 'prepare_manifest.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare animation authoring manifest.' }
& 'D:/FPS3D/FPSGAME/SourceAssets/WeaponSurface20260930/run_ue.ps1' -Script (Join-Path $PSScriptRoot 'install_profiles.py') -GateSeconds 3600
if ($LASTEXITCODE -ne 0) { throw 'Animation profile production did not complete.' }
& py -3.11 (Join-Path $PSScriptRoot 'summarize_receipt.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not record saved animation production counts.' }
