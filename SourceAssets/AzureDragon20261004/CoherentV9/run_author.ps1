param([string]$Blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
$ErrorActionPreference='Stop'
foreach($taskRecipe in @('claw','energy')){
    & $Blender --background --python-exit-code 1 --python (Join-Path $PSScriptRoot "author_$taskRecipe.py") *> (Join-Path $PSScriptRoot "author-$taskRecipe.log")
    if($LASTEXITCODE -ne 0){throw "V9 $taskRecipe export failed; see author-$taskRecipe.log."}
}
Write-Output 'V9 rig, animation and four closed 3D energy meshes exported; no rendering or game test.'
