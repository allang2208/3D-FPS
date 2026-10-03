param([string]$PlanPath = 'D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/Publication20261003/archive-plan.json')
$ErrorActionPreference = 'Stop'
$taskProject = [IO.Path]::GetFullPath('D:/FPS3D/FPSGAME').TrimEnd('\','/')
$taskArchive = [IO.Path]::GetFullPath('D:/FPS3D/FPSGAME/trash/blind-supplicant-m07-20261003').TrimEnd('\','/')
$taskReportPath = Join-Path $taskProject 'SourceAssets/BlindSupplicantM07Meshy20261001/Publication20261003/archive-manifest.json'
$taskAllowedRoots = @(
    (Join-Path $taskProject 'SourceAssets/BlindSupplicantM07Meshy20261001'),
    (Join-Path $taskProject 'Tools/BlindSupplicantM07'),
    (Join-Path $taskProject 'Content/Monsters/BlindSupplicantM07')
)
$taskPlan = Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskEntries = [Collections.Generic.List[object]]::new()
$taskReport = [ordered]@{ task = 'M07 pause and publication 20261003'; archive_root = $taskArchive; complete = $false; file_count = 0; bytes = [long]0; files = $taskEntries }
$taskUtf8 = [Text.UTF8Encoding]::new($false)
function Write-TaskReceipt {
    $taskReport.file_count = $taskEntries.Count
    [IO.File]::WriteAllText($taskReportPath, ($taskReport | ConvertTo-Json -Depth 8) + "`n", $taskUtf8)
}
if (Test-Path -LiteralPath $taskReportPath) {
    throw 'A prior archive receipt exists. Preserve it and resolve the recorded operation before starting another archive.'
}
# Resolve every final path before any move; no recursive shell operations.
$taskMoves = foreach ($taskItem in $taskPlan.files) {
    $taskSource = [IO.Path]::GetFullPath((Join-Path $taskProject $taskItem.path))
    $taskDestination = [IO.Path]::GetFullPath((Join-Path $taskArchive $taskItem.path))
    $taskInsideSource = $false
    foreach ($taskAllowedRoot in $taskAllowedRoots) {
        if ($taskSource.StartsWith($taskAllowedRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { $taskInsideSource = $true }
    }
    if (-not $taskInsideSource -or -not $taskDestination.StartsWith($taskArchive + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Archive path leaves M07 scope: $($taskItem.path)"
    }
    if (-not (Test-Path -LiteralPath $taskSource -PathType Leaf)) { throw "Missing archive source: $taskSource" }
    if (Test-Path -LiteralPath $taskDestination) { throw "Archive destination already exists: $taskDestination" }
    [pscustomobject]@{ Item = $taskItem; Source = $taskSource; Destination = $taskDestination }
}
Write-TaskReceipt
foreach ($taskMove in $taskMoves) {
    $taskFile = Get-Item -LiteralPath $taskMove.Source
    $taskHash = (Get-FileHash -LiteralPath $taskMove.Source -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($taskMove.Destination)) | Out-Null
    Move-Item -LiteralPath $taskMove.Source -Destination $taskMove.Destination
    $taskSaved = Get-Item -LiteralPath $taskMove.Destination
    $taskReadback = (Get-FileHash -LiteralPath $taskMove.Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    $taskEntry = [ordered]@{
        source = $taskMove.Item.path.Replace('\','/'); destination = $taskMove.Destination.Replace('\','/')
        bytes = $taskFile.Length; sha256 = $taskHash; reason = $taskMove.Item.reason; retained_replacement = $taskMove.Item.replacement
        readback_sha256 = $taskReadback; readback_equal = ($taskSaved.Length -eq $taskFile.Length -and $taskReadback -eq $taskHash)
    }
    $taskEntries.Add($taskEntry)
    $taskReport.bytes += $taskFile.Length
    Write-TaskReceipt
    if (-not $taskEntry.readback_equal) { throw "Archive readback differs: $($taskMove.Destination)" }
}
$taskReport.complete = $true
Write-TaskReceipt
[IO.Directory]::CreateDirectory($taskArchive) | Out-Null
[IO.File]::WriteAllText((Join-Path $taskArchive 'README.md'), "# M-07 recoverable archive`n`nOriginal paths, sizes, SHA-256, reasons and retained replacements are recorded in:`n`n$taskReportPath`n`nNo files were deleted. Do not run retired import scripts against the current character.`n", $taskUtf8)
Write-Output "M07 archived $($taskReport.file_count) files ($($taskReport.bytes) bytes). Receipt: $taskReportPath"
