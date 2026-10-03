param()
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$manifestPath = Join-Path $PSScriptRoot 'archive-manifest.json'
$archiveData = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$trashRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot 'trash/rsh12-pause-20261003'))
$allowedRoots = @('RSH12Integration20261003','RSH12SingleAction20261003','RSH12Fit20261003','RSH12FireFix20261003','RSH12Grip20261003') |
    ForEach-Object { [IO.Path]::GetFullPath((Join-Path $taskRoot ('SourceAssets/' + $_))) + [IO.Path]::DirectorySeparatorChar }
foreach ($entry in $archiveData.entries) {
    $sourcePath = [IO.Path]::GetFullPath((Join-Path $taskRoot $entry.original))
    $destinationPath = [IO.Path]::GetFullPath((Join-Path $taskRoot $entry.archived))
    $sourceInTask = @($allowedRoots | Where-Object { $sourcePath.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) }).Count -gt 0
    if (!$sourceInTask -or !$destinationPath.StartsWith($trashRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Archive path is outside this task'
    }
    if (Test-Path -LiteralPath $destinationPath) {
        if (Test-Path -LiteralPath $sourcePath) { throw ('Both source and archive exist: ' + $entry.original) }
    } else {
        if (!(Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw ('Missing source: ' + $entry.original) }
        if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Source changed after planning' }
        New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($destinationPath)) -Force | Out-Null
        Move-Item -LiteralPath $sourcePath -Destination $destinationPath
    }
    if ((Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Archived hash differs' }
}
$archiveData.state = 'moved_and_hash_verified'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$manifestText = ($archiveData | ConvertTo-Json -Depth 20) + [Environment]::NewLine
[IO.File]::WriteAllText($manifestPath, $manifestText, $utf8NoBom)
[IO.File]::WriteAllText((Join-Path $trashRoot 'manifest.json'), $manifestText, $utf8NoBom)
Write-Output ('RSH archive moved: ' + $archiveData.count + ' files; ' + $archiveData.bytes + ' bytes')
