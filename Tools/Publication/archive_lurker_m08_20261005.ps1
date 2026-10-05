$ErrorActionPreference = 'Stop'
$m08Project = [IO.Path]::GetFullPath('D:\FPS3D\FPSGAME')
$m08Source = Join-Path $m08Project 'SourceAssets\Monsters\LurkerM08'
$m08Trash = Join-Path $m08Project 'trash\lurker-m08-retired-20261005'
$m08Report = Join-Path $m08Project 'Docs\Publication\LurkerM08_20261005'
New-Item -ItemType Directory -Path $m08Report -Force | Out-Null
$m08Manifest = Join-Path $m08Report 'archive-manifest.json'
if (Test-Path -LiteralPath $m08Manifest) { throw 'An archive manifest already exists; do not overwrite an earlier archive.' }
$m08Rows = @()
foreach ($m08File in Get-ChildItem -LiteralPath $m08Source -Recurse -File) {
    $m08Relative = $m08File.FullName.Substring($m08Source.Length + 1).Replace('\','/')
    $m08Reason = $null
    $m08Replacement = 'Current M08 runtime/source files and retained authoring chain; see publication README.'
    if ($m08Relative -match '/(Before|PreviousSource)/' -or $m08File.Name -eq 'before_references.json') {
        $m08Reason = 'Superseded rollback snapshot, retained recoverably outside production source directories.'
    } elseif ($m08File.Extension -eq '.blend1') {
        $m08Reason = 'Blender previous-save backup; the corresponding final .blend is retained.'
        $m08Replacement = ('SourceAssets/Monsters/LurkerM08/' + $m08Relative.Substring(0,$m08Relative.Length-1))
    } elseif ($m08Relative -in @('Reference20261004/M08_turnaround_v01.png','Reference20261004/turnaround_prompt_v01.txt')) {
        $m08Reason = 'User rejected conflicting front/back structure; separate V02 references supersede this candidate.'
        $m08Replacement = 'SourceAssets/Monsters/LurkerM08/Reference20261004/v02'
    } elseif ($m08Relative -in @('DeathV10_20261005/read_support_vertex.py','DeathV10_20261005/support_vertex_source.json')) {
        $m08Reason = 'One-off support-vertex diagnosis; final death authoring uses its own complete skin support solve.'
        $m08Replacement = 'Tools/LurkerM08/author_death_v10.py'
    }
    if (-not $m08Reason) { continue }
    $m08From = [IO.Path]::GetFullPath($m08File.FullName)
    $m08To = [IO.Path]::GetFullPath((Join-Path $m08Trash ('SourceAssets\Monsters\LurkerM08\' + $m08Relative.Replace('/','\'))))
    if (-not $m08From.StartsWith($m08Source + '\',[StringComparison]::OrdinalIgnoreCase) -or
        -not $m08To.StartsWith($m08Trash + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive target escaped the M08 task boundary.' }
    if (Test-Path -LiteralPath $m08To) { throw ('Archive destination exists: ' + $m08To) }
    $m08Rows += [PSCustomObject]@{
        source = $m08From.Substring($m08Project.Length+1).Replace('\','/')
        destination = $m08To.Substring($m08Project.Length+1).Replace('\','/')
        bytes = $m08File.Length
        sha256 = (Get-FileHash -LiteralPath $m08From -Algorithm SHA256).Hash.ToLowerInvariant()
        reason = $m08Reason
        retained_replacement = $m08Replacement
        moved = $false
        hash_verified = $false
    }
}
$m08Plan = [PSCustomObject]@{task='lurker-m08-retired-20261005';scope='M08 source rollback and rejected candidates only';files=$m08Rows}
$m08Plan | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $m08Report 'archive-plan.json') -Encoding utf8
foreach ($m08Row in $m08Rows) {
    $m08From=Join-Path $m08Project $m08Row.source
    $m08To=Join-Path $m08Project $m08Row.destination
    if ((Get-FileHash -LiteralPath $m08From -Algorithm SHA256).Hash.ToLowerInvariant() -ne $m08Row.sha256) { throw 'Source changed after archive planning.' }
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($m08To)) -Force | Out-Null
    Move-Item -LiteralPath $m08From -Destination $m08To
    $m08Row.moved=$true
    $m08Row.hash_verified=(Get-FileHash -LiteralPath $m08To -Algorithm SHA256).Hash.ToLowerInvariant() -eq $m08Row.sha256
    $m08Plan | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $m08Manifest -Encoding utf8
    if (-not $m08Row.hash_verified) { throw ('Archived hash mismatch: ' + $m08Row.destination) }
}
$m08Plan | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $m08Manifest -Encoding utf8
Write-Output ('Archived ' + $m08Rows.Count + ' M08 files, ' + (($m08Rows | Measure-Object -Property bytes -Sum).Sum) + ' bytes; all moved hashes verified.')
