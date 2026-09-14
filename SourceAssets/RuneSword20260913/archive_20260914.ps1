param([ValidateSet('Plan','Move')][string]$Mode='Plan')
$ErrorActionPreference='Stop'
$runeProject=[IO.Path]::GetFullPath('D:\FPS3D\FPSGAME')
$runeSource=Join-Path $runeProject 'SourceAssets\RuneSword20260913'
$runeTrash=Join-Path $runeProject 'trash\runesword-melee-superseded-20260914'
$runeTemp=[IO.Path]::GetFullPath((Join-Path $env:TEMP 'RuneSwordGuardResearch20260914'))
$runeManifest=Join-Path $runeProject 'Docs\Weapons\runesword-archive-20260914.json'
function Within([string]$Path,[string]$Root) {
    $full=[IO.Path]::GetFullPath($Path);$base=[IO.Path]::GetFullPath($Root).TrimEnd('\')
    return $full.Equals($base,[StringComparison]::OrdinalIgnoreCase) -or $full.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase)
}
function Add-ArchiveTarget([string]$Path,[string]$Reason,[string]$Replacement) {
    if(!(Test-Path -LiteralPath $Path)){return}
    $resolved=(Resolve-Path -LiteralPath $Path).Path
    if(!(Within $resolved $runeSource) -and !(Within $resolved $runeTemp)){throw "Out of scope: $resolved"}
    if($resolved -eq $runeSource){throw 'Refuse entire authoring root'}
    if((Get-Item -LiteralPath $resolved -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Reparse target: $resolved"}
    $relative=if(Within $resolved $runeSource){[IO.Path]::GetRelativePath($runeProject,$resolved)}else{'TemporaryResearch\'+[IO.Path]::GetRelativePath((Split-Path $runeTemp),$resolved)}
    if($resolved -eq (Join-Path $runeSource 'README.md')){$relative='SourceAssets\RuneSword20260913\README.pre-workflow.md'}
    $destination=[IO.Path]::GetFullPath((Join-Path $runeTrash $relative))
    if(!(Within $destination $runeTrash) -or $destination -eq $runeTrash){throw "Unsafe destination: $destination"}
    $script:runeTargets.Add([pscustomobject]@{source=$resolved;destination=$destination;reason=$Reason;replacement=$Replacement})
}
if($Mode -eq 'Plan') {
    if(Test-Path -LiteralPath $runeManifest){throw 'Archive manifest already exists; use the recorded plan'}
    $runeTargets=[Collections.Generic.List[object]]::new()
    Add-ArchiveTarget (Join-Path $runeSource 'WeightedRhythmV7') 'Superseded timing attempt; V8 reads V6 directly' 'CompactRecoveryV8'
    Add-ArchiveTarget (Join-Path $runeSource 'ThrustComboV15') 'Superseded short thrust; V16 independently reads V12' 'StrideThrustV16'
    Get-ChildItem -LiteralPath $runeSource -Directory -Recurse -Force | Where-Object {
        $_.Name -in @('Before','NativeBuildSnapshot','__pycache__') -and
        !(Within $_.FullName (Join-Path $runeSource 'GuardParryV18\Before')) -and
        !(Within $_.FullName (Join-Path $runeSource 'GuardParryV18\NativeBuildSnapshot')) -and
        !(Within $_.FullName (Join-Path $runeSource 'GuardPoseV19\Before'))
    } | ForEach-Object {Add-ArchiveTarget $_.FullName 'Historical recovery/build/cache output; not an input of current authoring' 'Current sources, V18 native snapshot, V18/V19 rollback assets'}
    Get-ChildItem -LiteralPath $runeSource -File -Recurse -Filter '*.blend1' | ForEach-Object {
        $replacement=$_.FullName.Substring(0,$_.FullName.Length-1)
        if((Test-Path -LiteralPath $replacement) -and (Get-Item -LiteralPath $replacement).LastWriteTimeUtc -ge $_.LastWriteTimeUtc){Add-ArchiveTarget $_.FullName 'Superseded Blender backup with a newer editable source' $replacement}
    }
    Add-ArchiveTarget (Join-Path $runeSource 'GuardPoseV19\read_author_source.py') 'One-off authoring read; final author script reads its source directly' 'GuardPoseV19/author_guard.py'
    Add-ArchiveTarget (Join-Path $runeSource 'GuardPoseV19\accepted_idle_source.json') 'Unused dense pose read from licensed Manny source' 'GuardPoseV19/author_guard.py and retained Blend'
    Add-ArchiveTarget (Join-Path $runeSource 'GuardParryV18\author_guard_body.py') 'Assembly intermediate duplicated by the executable author script' 'GuardParryV18/author_guard.py'
    Add-ArchiveTarget (Join-Path $runeSource 'GuardParryV18\build-first-attempt.log') 'Superseded failed build log; final build log and result retained' 'GuardParryV18/build.log'
    Add-ArchiveTarget (Join-Path $runeSource 'README.md') 'Historical first-version entry; replaced with current V19 pause and V16/V17 baseline' 'README.md and Docs/Weapons/runesword-baseline-20260914.md'
    Add-ArchiveTarget $runeTemp 'Temporary public GitHub research clones; no current author/import references' 'GuardPoseV19/README.md reference provenance'
    $runeSelected=[Collections.Generic.List[object]]::new()
    foreach($target in ($runeTargets | Sort-Object {$_.source.Length})) {
        if(!@($runeSelected | Where-Object {Within $target.source $_.source}).Count){$runeSelected.Add($target)}
    }
    $runeRows=[Collections.Generic.List[object]]::new()
    foreach($target in $runeSelected) {
        if(Test-Path -LiteralPath $target.destination){throw "Destination exists: $($target.destination)"}
        $item=Get-Item -LiteralPath $target.source -Force
        $files=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $item.FullName -File -Recurse -Force)}else{@($item)}
        foreach($file in $files) {
            $dest=if($item.PSIsContainer){Join-Path $target.destination ([IO.Path]::GetRelativePath($target.source,$file.FullName))}else{$target.destination}
            if(!(Within $dest $runeTrash)){throw 'Unsafe file destination'}
            $runeRows.Add([pscustomobject]@{source=$file.FullName;destination=$dest;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash;reason=$target.reason;replacement=$target.replacement})
        }
    }
    $plan=[ordered]@{date='2026-09-14';status='planned';project=$runeProject;trash=$runeTrash;targets=@($runeSelected.ToArray());files=@($runeRows.ToArray());count=$runeRows.Count;bytes=($runeRows|Measure-Object bytes -Sum).Sum;preserved=@('Original/Reference and current asset dependency chain','ReachSweepV2 and V3/V4 key failure comparison inputs','WeightLeftV5 including ImportHost','V6 -> V8 -> V12 -> V16 -> V18 -> V19 editable source chain','Installed V19 guard remains paused and not accepted')}
    $plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $runeManifest -Encoding utf8
    [pscustomobject]@{status='planned';targets=$runeSelected.Count;files=$runeRows.Count;mb=[math]::Round($plan.bytes/1MB,2);manifest=$runeManifest} | ConvertTo-Json
    exit 0
}
$plan=Get-Content -LiteralPath $runeManifest -Raw | ConvertFrom-Json
if($plan.status -notin @('planned','archiving')){throw 'Only the recorded pending archive may be moved'}
foreach($row in $plan.files) {
    if(!(Within $row.source $runeSource) -and !(Within $row.source $runeTemp)){throw 'Source escaped authorized roots'}
    if(!(Within $row.destination $runeTrash)){throw 'Destination escaped trash'}
    $readPath=if(Test-Path -LiteralPath $row.source){$row.source}else{$row.destination}
    $item=Get-Item -LiteralPath $readPath -Force
    if($item.Length -ne $row.bytes -or (Get-FileHash -LiteralPath $readPath -Algorithm SHA256).Hash -ne $row.sha256){throw "Source/archive changed: $readPath"}
    if((Test-Path -LiteralPath $row.destination) -and (Get-FileHash -LiteralPath $row.destination -Algorithm SHA256).Hash -ne $row.sha256){throw 'Occupied destination with different content'}
}
$plan.status='archiving';$plan|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $runeManifest -Encoding utf8
foreach($target in $plan.targets) {
    if(!(Within $target.destination $runeTrash)){throw 'Invalid destination'}
    if(!(Test-Path -LiteralPath $target.source)){continue}
    $item=Get-Item -LiteralPath $target.source -Force
    if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Unexpected reparse target'}
    if($item.PSIsContainer) {
        $expected=@($plan.files | Where-Object {Within $_.source $target.source} | ForEach-Object {$_.source})
        foreach($file in (Get-ChildItem -LiteralPath $target.source -File -Recurse -Force)) {
            if($file.FullName -notin $expected){throw 'Uninventoried file appeared'}
        }
    }
}
foreach($row in $plan.files) {
    if(!(Test-Path -LiteralPath $row.source)){continue}
    New-Item -ItemType Directory -Path (Split-Path $row.destination) -Force | Out-Null
    Move-Item -LiteralPath $row.source -Destination $row.destination -Force
}
foreach($row in $plan.files) {
    if((Get-FileHash -LiteralPath $row.destination -Algorithm SHA256).Hash -ne $row.sha256){throw "Archive hash mismatch: $($row.destination)"}
}
foreach($target in $plan.targets) {
    if(!(Test-Path -LiteralPath $target.source -PathType Container)){continue}
    $dirs=@(Get-ChildItem -LiteralPath $target.source -Directory -Recurse -Force | Sort-Object {$_.FullName.Length} -Descending)
    $dirs+=Get-Item -LiteralPath $target.source -Force
    foreach($dir in $dirs) {
        $resolved=[IO.Path]::GetFullPath($dir.FullName)
        if(!(Within $resolved $target.source) -or (!(Within $resolved $runeSource) -and !(Within $resolved $runeTemp))){throw 'Unsafe empty-directory cleanup'}
        if(@(Get-ChildItem -LiteralPath $resolved -Force).Count -eq 0){Remove-Item -LiteralPath $resolved -Force}
    }
}
$plan.status='archived';$plan|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $runeManifest -Encoding utf8
[pscustomobject]@{status='archived';files=$plan.count;mb=[math]::Round($plan.bytes/1MB,2);trash=$runeTrash}|ConvertTo-Json
