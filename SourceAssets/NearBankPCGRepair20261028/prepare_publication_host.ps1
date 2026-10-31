$ErrorActionPreference='Stop'
$pubRoot=[IO.Path]::GetFullPath("$PSScriptRoot/PublicationHost")
if(-not $pubRoot.StartsWith([IO.Path]::GetFullPath($PSScriptRoot)+[IO.Path]::DirectorySeparatorChar)){throw 'Invalid publication directory'}
if(Test-Path -LiteralPath $pubRoot){throw 'Publication host already exists; preserve it'}
$project='D:/FPS3D/FPSGAME'
New-Item -ItemType Directory -Path $pubRoot | Out-Null
Copy-Item -LiteralPath "$project/Config" -Destination "$pubRoot/Config" -Recurse
New-Item -ItemType Junction -Path "$pubRoot/Binaries" -Target "$project/Binaries" | Out-Null
New-Item -ItemType Directory -Path "$pubRoot/Content" | Out-Null
foreach($entry in Get-ChildItem -LiteralPath "$project/Content") {
 if($entry.Name -in @('GameMaps','NativeNearBank20261028')) {Copy-Item -LiteralPath $entry.FullName -Destination "$pubRoot/Content/$($entry.Name)" -Recurse}
 elseif($entry.PSIsContainer){New-Item -ItemType Junction -Path "$pubRoot/Content/$($entry.Name)" -Target $entry.FullName | Out-Null}
 else {Copy-Item -LiteralPath $entry.FullName -Destination "$pubRoot/Content/$($entry.Name)"}
}
$descriptor=Get-Content -LiteralPath "$project/FPSGAME.uproject" -Raw | ConvertFrom-Json
$descriptor | Add-Member -NotePropertyName AdditionalPluginDirectories -NotePropertyValue @("$project/Plugins") -Force
$descriptor | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath "$pubRoot/FPSGAME.uproject" -Encoding utf8
