param([Parameter(Mandatory=$true)][string]$SourceRoot)
$ErrorActionPreference = 'Stop'
$studyContent = Join-Path (Split-Path -Parent $PSScriptRoot) 'Content'
foreach ($entry in @(
    @{Pack='EuropeanHornbeam'; Folder='EuropeanHornbeam'},
    @{Pack='CommonHazel'; Folder='CommonHazel'},
    @{Pack='EuropeanHornbeam'; Folder='MSPresets'}
)) {
    $packageRoot = Join-Path $SourceRoot ('Fab/' + $entry.Pack)
    if (-not (Test-Path -LiteralPath (Join-Path $packageRoot 'epic.manifest'))) {
        throw ('Incomplete Epic source pack: ' + $entry.Pack)
    }
    $folder = Join-Path $packageRoot ('Content/' + $entry.Folder)
    $dest = Join-Path $studyContent $entry.Folder
    # Preserve any local art edits. The Hornbeam bundle includes every shared preset used by Hazel.
    & robocopy $folder $dest /E /XC /XN /XO /R:1 /W:2 /NP /NFL /NDL /NJH /NJS
    if ($LASTEXITCODE -ge 8) { throw ('Copy failed: ' + $folder) }
}
exit 0
