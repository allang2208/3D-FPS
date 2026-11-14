$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$uv=Join-Path $r 'tile-uv.json'
$start=Get-Date
while(!(Test-Path -LiteralPath $uv)){
    if(Test-Path (Join-Path $r 'error-07.txt')){throw (Get-Content (Join-Path $r 'error-07.txt') -Raw)}
    if(((Get-Date)-$start).TotalMinutes -gt 40){throw 'Timed out waiting for UE source UVs'}
    Start-Sleep -Seconds 2
}
& python (Join-Path $r 'patch_tiles.py')
if($LASTEXITCODE -ne 0){throw 'Tile repair layout failed'}
$export=(Get-Content (Join-Path $r 'export_meshes.py') -Raw).Replace("'panels.json'","'repairs.json'")
$exportPath=Join-Path $r 'export_tiles.py'
[IO.File]::WriteAllText($exportPath,$export)
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b -t 3 --python-exit-code 1 --python $exportPath *> (Join-Path $r 'export-tiles.log')
if($LASTEXITCODE -ne 0){throw 'Tile repair mesh export failed'}
$job=Join-Path $r 'job-08.json'
if(!(Test-Path $job)){
    [IO.File]::WriteAllText(($job+'.tmp'),'{"script":"install_tiles.py","photo":"after","save":true}')
    [IO.File]::Move(($job+'.tmp'),$job)
}
