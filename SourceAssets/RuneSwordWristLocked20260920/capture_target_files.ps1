$ErrorActionPreference='Stop'
$root='D:\FPS3D\FPSGAME'
$prior=Get-Content (Join-Path $root 'SourceAssets\RuneSwordElbowRepair20260920\import_receipt.json') -Raw | ConvertFrom-Json
$targets=@{}
foreach($entry in $prior.saved.PSObject.Properties) {
    $package=($entry.Value.asset -split '\.')[0]
    $file=Join-Path $root ('Content\'+$package.Substring(6).Replace('/','\')+'.uasset')
    $targets[$entry.Name]=@{asset=$entry.Value.asset;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$targets | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'target_inputs.json') -Encoding utf8
