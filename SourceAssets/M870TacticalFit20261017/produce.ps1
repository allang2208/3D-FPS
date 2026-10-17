$ErrorActionPreference='Stop'
$deadline=[DateTime]::UtcNow.AddMinutes(45)
while(-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'inputs.json'))) {
    if([DateTime]::UtcNow -gt $deadline){throw 'Current M870 surface extraction has not completed.'}
    Start-Sleep -Seconds 5
}
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b -t 2 --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author.py') *> (Join-Path $PSScriptRoot 'author.log')
if($LASTEXITCODE -ne 0){throw 'M870 tactical fitting failed; see author.log.'}
& (Join-Path $PSScriptRoot 'run_asset.ps1') -Script 'import_assets.py' *> (Join-Path $PSScriptRoot 'import_console.log')
if($LASTEXITCODE -ne 0){throw 'M870 tactical import failed.'}
$receipt=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'import_receipt.json') -Raw | ConvertFrom-Json
if(-not $receipt.completed){throw 'M870 tactical assets were not saved.'}
& 'D:/FPS3D/FPSGAME/Tools/Weapons/M870ThirdPerson20261017/build.ps1' *> (Join-Path $PSScriptRoot 'build_editor.log')
if($LASTEXITCODE -ne 0){throw 'M870 tactical source build did not succeed.'}
Write-Output 'M870 tactical meshes saved and Editor build complete.'
