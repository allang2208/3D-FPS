$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$job=Join-Path $project 'SourceAssets/M870CommonOptics20261016'
$blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
Push-Location $project
try {
    if(-not (Test-Path -LiteralPath "$job/inputs.json")){ & "$job/read_inputs.ps1" }
    & $blender -b --python "$job/author_adapters.py" *> "$job/author_adapters.log"
    if($LASTEXITCODE -ne 0){throw 'Adapter export failed.'}
    & $blender -b --python "$job/sample_finish_uv.py" *> "$job/sample_finish_uv.log"
    if($LASTEXITCODE -ne 0){throw 'Rail surface source read failed.'}
    python "$job/author_finish.py"
    if($LASTEXITCODE -ne 0){throw 'Material authoring failed.'}
    python "$job/register_catalog.py"
    if($LASTEXITCODE -ne 0){throw 'Catalog update failed.'}
    & "$project/Tools/Build/Build-Editor.ps1" *> "$job/build_editor_final.log"
    & "$job/install_assets.ps1" *> "$job/install_console.log"
} finally { Pop-Location }
