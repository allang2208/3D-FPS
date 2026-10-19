param([string]$ReceiptName=('asset-save-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
Push-Location $projectRoot
try{
    & python Tools/TrouserFit/prepare.py
    if($LASTEXITCODE -ne 0){throw 'Waist source preparation failed.'}
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b -t 6 --python Tools/TrouserFit/save_editable.py
    if($LASTEXITCODE -ne 0){throw 'Editable and icon export failed.'}
    & Tools/TrouserFit/run_asset.ps1 -ReceiptName $ReceiptName
    if($LASTEXITCODE -ne 0){throw 'Asset save incomplete; current config remains unchanged.'}
}finally{Pop-Location}
