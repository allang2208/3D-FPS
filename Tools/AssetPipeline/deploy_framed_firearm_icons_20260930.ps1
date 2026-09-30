$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$sourceRoot = Join-Path $projectRoot 'SourceAssets/FirearmFramedIcons20260930'
$destinationRoot = Join-Path $projectRoot 'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
$manifest = Get-Content -LiteralPath (Join-Path $sourceRoot 'manifest.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
$copied = 0
$pending = @()
foreach ($group in $manifest.groups) {
    $sourceImage = Join-Path $sourceRoot ('Generated/'+$group[0]+'.png')
    if (-not (Test-Path -LiteralPath $sourceImage)) { $pending += $group[0]; continue }
    foreach ($key in $group) {
        Copy-Item -LiteralPath $sourceImage -Destination (Join-Path $destinationRoot ($key+'.png')) -Force
        $copied++
    }
}
@{ copied=$copied; pending=$pending } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $sourceRoot 'deployment_result.json') -Encoding UTF8
Write-Output "Deployed $copied icons; pending $($pending.Count) source groups."
