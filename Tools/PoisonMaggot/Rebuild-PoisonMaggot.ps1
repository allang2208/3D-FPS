param([ValidateSet('Generated','Topology','Rig','Import','Preview','Village')][string]$From='Import')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$taskPython='C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe'
$taskEditor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
Set-Location -LiteralPath $taskRoot
function Run-Author([string]$Name) {
    & $taskBlender -b -t 4 --python-exit-code 1 --python ('Tools/PoisonMaggot/'+$Name)
    if($LASTEXITCODE -ne 0){throw "Blender failed: $Name"}
}
function Run-Import([string]$Name,[string]$Marker) {
    $taskLog=$taskRoot+'/Saved/PoisonMaggot/rebuild-'+[IO.Path]::GetFileNameWithoutExtension($Name)+'.log'
    & $taskEditor ($taskRoot+'/FPSGAME.uproject') -run=pythonscript ('-script='+$taskRoot+'/Tools/PoisonMaggot/'+$Name) -unattended -AllowCommandletRendering ('-abslog='+$taskLog)
    # The host has unrelated GameFeatureData commandlet warnings; require our
    # completion marker AND no Python exception, not just the process exit code.
    $taskText=Get-Content -LiteralPath $taskLog -Raw
    if($taskText -notmatch $Marker -or $taskText -match 'Traceback \(most recent call last\)'){throw "Import failed: $Name; inspect $taskLog"}
}
if($From -eq 'Generated') {
    if(!(Test-Path -LiteralPath 'Saved/Hunyuan3D/Candidates/poison_maggot_v01/asset_01.glb')){throw 'Restore the existing generated GLB first; this script never submits a paid generation job.'}
    Run-Author 'inspect_raw.py'
    Run-Author 'build_topology.py'
}
if($From -eq 'Topology'){Run-Author 'build_topology.py'}
if($From -in @('Generated','Topology','Rig')) {
    Run-Author 'rig_animate.py'
    & $taskPython 'Tools/PoisonMaggot/prepare_media.py'
    if($LASTEXITCODE -ne 0){throw 'Media preparation failed'}
}
if($From -in @('Generated','Topology','Rig','Import')){Run-Import 'import_maggot.py' 'MAGGOT_IMPORT_COMPLETE'}
if($From -eq 'Preview') {
    Run-Author 'verify_render.py'
    & $taskPython 'Tools/PoisonMaggot/encode_previews.py'
    if($LASTEXITCODE -ne 0){throw 'Preview encoding failed'}
}
if($From -eq 'Village'){Run-Import 'place_village.py' 'MAGGOT_VILLAGE_SAVED'}
