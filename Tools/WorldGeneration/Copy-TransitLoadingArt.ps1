param([string]$SourceProject='E:\无尽轮回\长期备份\2026-7-13-1\game-dev')
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$TargetDirectory=Join-Path $ProjectRoot 'Content/UI/TransitLoading'
New-Item -ItemType Directory -Path $TargetDirectory -Force | Out-Null
foreach($Variant in 1,2) {
    $FileName="gaia-fertile-lands-$Variant.png"
    Copy-Item -LiteralPath (Join-Path $SourceProject "assets/scenes/loading/main-hub/$FileName") -Destination (Join-Path $TargetDirectory $FileName)
}
Write-Output "Copied game-dev loading backgrounds to $TargetDirectory"
