$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$sourceRoot = Join-Path $projectRoot 'SourceAssets/BowFramedIcons20260930'
$destinationRoot = Join-Path $projectRoot 'Content/ColdSteelData/AttachmentIcons20260913/FramedBows'
$manifest = Get-Content -LiteralPath (Join-Path $sourceRoot 'manifest.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
$legacyRoot = Join-Path $projectRoot 'Content/ColdSteelData/AttachmentIcons20260913'
$backupRoot = Join-Path $projectRoot 'trash/modification-icons-20260930/BowFramedIcons20260930/Original'
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$copied = 0
$pending = @()
foreach ($group in $manifest.groups) {
    $sourceImage = Join-Path $sourceRoot ('Generated/'+$group[0]+'.png')
    if (-not (Test-Path -LiteralPath $sourceImage)) { $pending += $group[0]; continue }
    foreach ($key in $group) {
        Copy-Item -LiteralPath $sourceImage -Destination (Join-Path $destinationRoot ($key+'.png')) -Force
        $legacyImage = Join-Path $legacyRoot ($key+'.png')
        $backupImage = Join-Path $backupRoot ($key+'.png')
        if ((Test-Path -LiteralPath $legacyImage) -and -not (Test-Path -LiteralPath $backupImage)) { Copy-Item -LiteralPath $legacyImage -Destination $backupImage }
        Copy-Item -LiteralPath $sourceImage -Destination $legacyImage -Force
        $copied++
    }
}
@{ copied=$copied; pending=$pending } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $sourceRoot 'deployment_result.json') -Encoding UTF8
Write-Output "Deployed $copied icons; pending $($pending.Count) source groups."
