$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$stage=Join-Path $root 'Saved/WoodworkingCrystalBench/SurfaceHost'
$namespace='Building/WoodworkingCrystalBench/Surfaces'
$destination=Join-Path "$root/Content" $namespace
$hostContent="$stage/Content"
$scan='WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces'
New-Item -ItemType Directory -Force "$hostContent/$scan",$destination | Out-Null
Get-ChildItem "$root/Content/$scan" -Filter T_ChapelTimber_*.uasset | Copy-Item -Destination "$hostContent/$scan" -Force
@{FileVersion=3; EngineAssociation='5.8'; Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 "$stage/BenchSurfaces.uproject"
$config=Join-Path $stage 'Config'
New-Item -ItemType Directory -Force $config | Out-Null
@(
  '[/Script/WindowsTargetPlatform.WindowsTargetSettings]'
  'DefaultGraphicsRHI=DefaultGraphicsRHI_DX12'
  '-D3D12TargetedShaderFormats=PCD3D_SM5'
  '+D3D12TargetedShaderFormats=PCD3D_SM6'
  '[/Script/Engine.RendererSettings]'
  'r.Substrate=True'
  'r.Substrate.ProjectGBufferFormat=0'
) | Set-Content -LiteralPath "$config/DefaultEngine.ini" -Encoding utf8
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$argsList=@(('"'+$stage+'/BenchSurfaces.uproject"'),'-run=pythonscript',('-script="'+$PSScriptRoot+'/author.py"'),'-unattended','-nop4','-nosplash','-nosound','-Multiprocess','-d3d12','-RenderOffscreen','-AllowCommandletRendering',('-abslog="'+$stage+'/author-'+$stamp+'.log"'))
$p=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
$null=$p.Handle
$p.WaitForExit()
$p.Refresh()
if($p.ExitCode){throw "Surface build exited with $($p.ExitCode), see $stage/author-$stamp.log"}
$list=Get-Content -LiteralPath "$PSScriptRoot/packages.json" -Raw | ConvertFrom-Json
$binding=Get-Content -LiteralPath "$PSScriptRoot/bindings-staged.json" -Raw | ConvertFrom-Json
foreach($path in $binding.psobject.Properties.Value){
  $production="$root/Content/"+$path.Substring(6)+'.uasset'
  if($path -notin $list -and !(Test-Path -LiteralPath $production)){throw "Missing village material $path"}
}
$lock=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000'); $held=$false
try {
  try {$held=$lock.WaitOne()}catch [Threading.AbandonedMutexException] {$held=$true}
  $previous=if(Test-Path -LiteralPath "$PSScriptRoot/installed.json"){Get-Content -Raw -LiteralPath "$PSScriptRoot/installed.json" | ConvertFrom-Json}
  $ed=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -like '*FPSGAME.uproject*' -or !$_.CommandLine}
  $rows=foreach($path in $list){
    if(!$path.StartsWith("/Game/$namespace/")){throw "Unexpected package $path"}
    $name=$path.Split('/')[-1]+'.uasset'
    $src="$hostContent/$namespace/$name"
    $dst="$destination/$name"
    $hash=(Get-FileHash -LiteralPath $src).Hash
    $original=if(Test-Path -LiteralPath $dst){(Get-FileHash -LiteralPath $dst).Hash}
    if($original -and $original -ne $hash){
      if($ed){throw "Existing material open in project context: $dst"}
      if(!($previous | Where-Object {$_.asset -eq $path -and $_.sha256 -eq $original})){throw "Unexpected material version at $dst"}
    }
    [PSCustomObject]@{asset=$path;source=$src;destination=$dst;sha256=$hash;bytes=(Get-Item -LiteralPath $src).Length;changed=$hash -ne $original}
  }
  foreach($row in $rows | Where-Object changed){
    $temp=$row.destination+'.incoming'
    [IO.File]::Copy($row.source,$temp,$true)
    if([IO.File]::Exists($row.destination)){[IO.File]::Replace($temp,$row.destination,$null)}else{[IO.File]::Move($temp,$row.destination)}
  }
  $rows | Select-Object asset,sha256,bytes | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 "$PSScriptRoot/installed.json"
  Copy-Item -LiteralPath "$PSScriptRoot/bindings-staged.json" -Destination "$PSScriptRoot/materials.json" -Force
  $rows | Select-Object asset,bytes
}finally{ if($held){$lock.ReleaseMutex()};$lock.Dispose() }
