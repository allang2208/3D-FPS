# Retire the superseded rounds of the AKM / A762 reload thumb work into trash/.
#
# Keeps the accepted round (v4) and every input/diagnostic the accepted recipe
# still uses; moves each rejected or superseded round's exports, backups, scripts
# and renders to trash/AKMA762GripTwist20260925/ with a SHA-256 manifest
# (WORKFLOW.md section 4).  Within the same volume the move is a rename, so the
# 19 GB of superseded exports cost no copy time; only the hashing reads them.
$ErrorActionPreference = 'Stop'
$task = 'D:\FPS3D\FPSGAME\SourceAssets\AKMA762GripTwist20260925'
$trashRoot = 'D:\FPS3D\FPSGAME\trash\AKMA762GripTwist20260925'

# --- what stays -------------------------------------------------------------
$keepFiles = @(
    'README.md',
    # round 1 (twist repair) - the shipping root is still read from its receipt,
    # and thumb_fit.json still provides the comparison pose in verify4
    'author_thumb.py', 'authoring.json', 'verify_thumb.py', 'verify_thumb.json',
    'install.py', 'install_receipt.json', 'run_import.ps1',
    'fit_thumb.py', 'thumb_fit.json', 'thumb_reference.json',
    'twist_audit4.py', 'twist_split.py', 'thumb_contact.py', 'thumb_opposition.py',
    'twist_audit4.json', 'twist_split.json', 'thumb_contact.json', 'thumb_opposition.json',
    'render_thumb_fit.py', 'render_hand.py', 'render_grip2.py',
    # reference / rig diagnostics the accepted recipe rests on
    'ref_thumb.py', 'probe_heads.py', 'rest_chain.py', 'probe_mag2.py', 'probe_mag3.py',
    # accepted round inputs: the natural extension (v3 target) and the web metric
    'select_target3.py', 'thumb_target3.json', 'web_check2.py', 'thumb_web_check.json',
    # accepted round: crossing discovery, direction search, authoring, verification, import
    'thumb_index.py', 'thumb_index.json', 'render_index.py', 'render_thumb6.json',
    'select_target4.py', 'thumb_target4.json', 'author_thumb4.py', 'authoring4.json',
    'verify4.py', 'verify4_00.json', 'verify4_10.json', 'verify4_20.json',
    'install4.py', 'install4_receipt.json', 'readback4.py', 'readback4.json',
    'run_import4.ps1', 'run_readback4.ps1', 'archive_superseded.ps1',
    'ue-import.log', 'ue-import4.log', 'author4.log',
    'verify4_00.log', 'verify4_10.log', 'verify4_20.log', 'verify4.log',
    'select_target4.log', 'thumb_index.log', 'render_index.log', 'web_check2.log'
)
$keepDirs = @('v4')
$keepPngPrefix = 'thumb6_'      # the renders that decided the accepted direction

function Get-Reason([string]$name, [bool]$isDir, [bool]$isPng) {
    if ($isDir) {
        switch ($name) {
            'v2' { return 'round-2 exports: rejected - swinging the root 74/79 deg stretched the web (web gap +33 %, 62-65 mm of web skin moved)' }
            'v3' { return 'round-3 exports: superseded by round 4 - the straightened thumb crossed the index finger' }
            'AKM' { return 'round-1 exports (AKM): superseded by the accepted round-4 exports' }
            'A762' { return 'round-1 exports (A762): superseded by the accepted round-4 exports' }
            'Before' { return 'round-1 package backup: superseded, the round-1 state is described by authoring.json and thumb_fit.json' }
            'Before2' { return 'round-2 package backup: rejected round' }
            'Before3' { return 'round-3 package backup: superseded by round 4' }
            'Before4' { return 'round-3 package backup taken while importing round 4: superseded by round 4' }
            default { return 'superseded directory' }
        }
    }
    if ($isPng -and -not $name.StartsWith($keepPngPrefix)) {
        return 'render from a rejected or superseded round; the accepted direction is shown by thumb6_*.png'
    }
    switch -Regex ($name) {
        '^(aim_thumb|aim_visual|aim_vis2)\.py$' { return 'turn-5 aiming attempts: superseded by the closed-form visible-direction aim (aim_vis2) and then by the root-preserving round 3' }
        '^thumb_aim' { return 'turn-5 aim candidate dumps: superseded' }
        '^thumb_fit2|^fit_thumb2' { return 'turn-5 refit attempt: superseded by the web measurement and the root-preserving round 3' }
        '^(probe_mag|sweep_thumb|score_thumb|search_thumb)' { return 'turn-5 exploration: superseded by probe_mag2/3, web_check2 and thumb_index' }
        '^web_check\.py$' { return 'first web check: used the round-1 root without its swing-only projection; web_check2 is authoritative' }
        '^select_target\.py$|^thumb_target2|^author_thumb2|^authoring2|^verify2|^install2|^readback2|^family_check|^twist_added|^render_(aim|side|final)|^render_thumb3|^render_thumb4|^thumb4_' { return 'round-2 (v2) pipeline: rejected - the root swing stretched the web' }
        '^author_thumb3|^authoring3|^verify3|^install3|^readback3|^render_v3|^render_thumb5|^thumb5_' { return 'round-3 (v3) pipeline: superseded by round 4 (thumb crossed the index finger)' }
        '\.log$' { return 'log from a rejected or superseded round' }
        default { return 'superseded by the accepted round-4 pipeline' }
    }
}

$moves = @()
foreach ($item in Get-ChildItem $task -Force) {
    if ($item.Name -like '.*') { continue }
    $isDir = $item.PSIsContainer
    $isPng = (-not $isDir) -and $item.Extension -eq '.png'
    if ($isDir -and ($keepDirs -contains $item.Name)) { continue }
    if (-not $isDir -and ($keepFiles -contains $item.Name)) { continue }
    if ($isPng -and $item.Name.StartsWith($keepPngPrefix)) { continue }
    $moves += [pscustomobject]@{
        Name = $item.Name
        IsDir = $isDir
        Reason = (Get-Reason $item.Name $isDir $isPng)
    }
}

Write-Output ("files/directories to retire: {0}" -f $moves.Count)
$totalBytes = 0
foreach ($m in $moves) {
    $p = Join-Path $task $m.Name
    if ($m.IsDir) {
        $s = (Get-ChildItem $p -Recurse -File | Measure-Object Length -Sum).Sum
    } else {
        $s = (Get-Item $p).Length
    }
    $totalBytes += $s
    Write-Output ("  {0,-34} {1,10:N2} MB  {2}" -f $m.Name, ($s / 1MB), $m.Reason)
}
Write-Output ("total: {0:N2} GB" -f ($totalBytes / 1GB))

if ($env:ARCHIVE_DRYRUN -eq '1') { Write-Output 'DRY RUN ONLY'; return }

# --- move + hash ------------------------------------------------------------
$manifest = @()
New-Item -ItemType Directory -Force -Path $trashRoot | Out-Null
foreach ($m in $moves) {
    $src = Join-Path $task $m.Name
    $dst = Join-Path $trashRoot $m.Name
    $srcFull = (Resolve-Path -LiteralPath $src).Path
    if (-not $srcFull.StartsWith($task, [StringComparison]::OrdinalIgnoreCase)) {
        throw "refusing to move outside the task folder: $srcFull"
    }
    Move-Item -LiteralPath $src -Destination $dst -Force
    if (Test-Path -LiteralPath $src) { throw "source still present after move: $src" }
    if (-not (Test-Path -LiteralPath $dst)) { throw "destination missing after move: $dst" }
    $targets = if (Test-Path -LiteralPath $dst -PathType Container) {
        Get-ChildItem -LiteralPath $dst -Recurse -File
    } else {
        Get-Item -LiteralPath $dst
    }
    foreach ($t in $targets) {
        $rel = $t.FullName.Substring($trashRoot.Length).TrimStart('\')
        $orig = Join-Path $task $rel
        $manifest += [pscustomobject]@{
            original_path = $orig
            trash_path = $t.FullName
            bytes = $t.Length
            sha256 = (Get-FileHash -LiteralPath $t.FullName -Algorithm SHA256).Hash.ToLower()
            reason = $m.Reason
            replacement = 'SourceAssets/AKMA762GripTwist20260925 (accepted round 4: v4/ exports, thumb_target4.json, verify4_*.json, install4.py, readback4.json)'
        }
    }
    Write-Output ("moved {0} ({1} files)" -f $m.Name, @($targets).Count)
}
$manifestJson = [pscustomobject]@{
    task = 'AKMA762GripTwist20260925'
    archived_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    note = 'Superseded rounds of the AKM / A762 reload thumb work. Binaries and renders stay local; this folder is git-ignored.'
    entries = $manifest
}
$manifestJson | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $trashRoot 'manifest.json') -Encoding UTF8
Write-Output ("ARCHIVE_OK entries={0} sha256_recorded={1}" -f $manifest.Count, ($manifest | Where-Object { $_.sha256 }).Count)
