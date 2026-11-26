$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$stageRoot = Join-Path $projectRoot 'SourceAssets\ModernTacticalSet20261113\CombatShirtR4\StageHost'
$stageContent = Join-Path $stageRoot 'Content'
$ownedBranch = @('Characters','ModularOutfit20260924','ModernTacticalSet20261113','CombatShirtR4')
function Mount-Branch([string]$source,[string]$target,[int]$depth) {
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    foreach ($entry in Get-ChildItem -LiteralPath $source) {
        $destination = Join-Path $target $entry.Name
        if ($depth -lt $ownedBranch.Count -and $entry.Name -eq $ownedBranch[$depth]) {
            if ($depth -eq $ownedBranch.Count-1) { New-Item -ItemType Directory -Path $destination -Force | Out-Null }
            else { Mount-Branch $entry.FullName $destination ($depth+1) }
        } elseif (-not (Test-Path -LiteralPath $destination)) {
            if ($entry.PSIsContainer) { New-Item -ItemType Junction -Path $destination -Target $entry.FullName | Out-Null }
            else { Copy-Item -LiteralPath $entry.FullName -Destination $destination }
        }
    }
    if ($depth -lt $ownedBranch.Count -and -not (Test-Path -LiteralPath (Join-Path $target $ownedBranch[$depth]))) {
        New-Item -ItemType Directory -Path (Join-Path $target ($ownedBranch[$depth..($ownedBranch.Count-1)] -join '\')) -Force | Out-Null
    }
}
Mount-Branch (Join-Path $projectRoot 'Content') $stageContent 0
$plugins = @('PythonScriptPlugin','EditorScriptingUtilities','GeometryScripting','HairStrands','RigLogic','FullBodyIK','SkeletalReduction','Interchange','InterchangeEditor') | ForEach-Object { @{Name=$_;Enabled=$true} }
@{FileVersion=3;EngineAssociation='5.8';DisableEnginePluginsByDefault=$true;Plugins=$plugins} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stageRoot 'TS01CombatR4.uproject') -Encoding utf8
$leanRoot = Join-Path (Split-Path $stageRoot) 'StageHostLean'
New-Item -ItemType Directory -Path (Join-Path $leanRoot 'Content\Characters') -Force | Out-Null
$mounts = @{}
foreach ($name in @('AsianMale_Jason','Weapons','Items')) { $mounts[$name] = Join-Path $projectRoot ('Content\'+$name) }
foreach ($name in @('Mannequins','KaitlinPlayer20261023','BackpackFit20261024','SimpleSlingBag20261022')) { $mounts['Characters\'+$name] = Join-Path $projectRoot ('Content\Characters\'+$name) }
$mounts['Characters\ModularOutfit20260924'] = Join-Path $stageContent 'Characters\ModularOutfit20260924'
foreach ($relative in $mounts.Keys) {
    $destination = Join-Path $leanRoot ('Content\'+$relative)
    if (-not (Test-Path -LiteralPath $destination)) { New-Item -ItemType Junction -Path $destination -Target $mounts[$relative] | Out-Null }
}
Copy-Item -LiteralPath (Join-Path $stageRoot 'TS01CombatR4.uproject') -Destination (Join-Path $leanRoot 'TS01CombatR4.uproject') -Force
Write-Output 'R4_STAGE_READY'
