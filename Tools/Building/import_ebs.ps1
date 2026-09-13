param([string]$Source='D:/FPS3D/EasyBuildingSystemV10/Content/EasyBuildingSystem')
$ErrorActionPreference='Stop'
$destination='D:/FPS3D/FPSGAME/Content/EasyBuildingSystem'
if(Test-Path -LiteralPath $destination){Write-Output 'EBS content is already present; keeping existing files.';return}
Copy-Item -LiteralPath $Source -Destination $destination -Recurse
Write-Output 'Imported EBS content library. Character, GameMode, input and project settings were not replaced.'
