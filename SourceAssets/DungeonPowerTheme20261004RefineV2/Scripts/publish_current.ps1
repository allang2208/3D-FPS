[CmdletBinding()]
param([switch]$AuthorizeProjectWrites)
$ErrorActionPreference='Stop'
if (-not $AuthorizeProjectWrites) { throw 'Explicit publication authorization required' }
$taskProject='D:\FPS3D\FPSGAME'
$taskRoot=Join-Path $taskProject 'SourceAssets\DungeonPowerTheme20261004RefineV2'
$exe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$receipts=Join-Path $taskRoot 'Receipts'
$plan=Get-Content -LiteralPath (Join-Path $taskRoot 'Config\local-publication-plan.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
function HashOf([string]$file) { (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() }
function CheckIdle {
    $active=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor')
    })
    if ($active.Count) { throw ('Preserve current UE/build processes: '+($active.ProcessId -join ',')) }
}
function RunStage([string]$script) {
    CheckIdle
    $log=Join-Path $receipts ($script.Replace('.py','')+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    & $exe (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' ('-script='+(Join-Path $taskRoot ('Scripts\'+$script))) '-PowerThemeAuthorizeWrite' '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$log) *> ($log+'.stdout')
    if ($LASTEXITCODE -ne 0) { throw ($script+' failed; preserve '+$log) }
}
function SaveJson($object,[string]$path) { $object | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $path -Encoding UTF8 }
try {
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    while (-not $held -and [DateTime]::UtcNow -lt $deadline) {
        try { $held=$taskGate.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $held=$true }
    }
    if (-not $held) { throw 'Shared UE batch mutex remains busy' }
    CheckIdle
    RunStage 'audit_publication.py'
    $audit=Get-Content -LiteralPath (Join-Path $receipts 'publication-reference-audit.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($audit.stage -ne 'reference_audit_saved') { throw 'Actual reference audit receipt absent' }
    $archiveRoot=[IO.Path]::GetFullPath((Join-Path $taskProject ('trash\PowerTheme20261004-ReplacedByRefineV2-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))))
    if (-not $archiveRoot.StartsWith(($taskProject+'\trash\PowerTheme20261004-ReplacedByRefineV2-'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive escaped owned root' }
    New-Item -ItemType Directory -Path $archiveRoot | Out-Null
    $moves=[Collections.Generic.List[object]]::new()
    function ArchiveFile([string]$source,[string]$sha,[string]$relative) {
        $resolved=(Resolve-Path -LiteralPath $source).Path
        $target=[IO.Path]::GetFullPath((Join-Path $archiveRoot $relative))
        if (-not $resolved.StartsWith(($taskProject+'\'),[StringComparison]::OrdinalIgnoreCase) -or -not $target.StartsWith(($archiveRoot+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path outside project/scope' }
        if ((HashOf $resolved) -ne $sha) { throw ('File changed, preserve: '+$resolved) }
        if (Test-Path -LiteralPath $target) { throw 'Do not overwrite recovery archive' }
        New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
        Move-Item -LiteralPath $resolved -Destination $target
        if ((HashOf $target) -ne $sha) { throw 'Archived hash differs' }
        $moves.Add([pscustomobject]@{source=$resolved;archive=$target;sha256=$sha;kind='file'})
        SaveJson @($moves.ToArray()) (Join-Path $archiveRoot 'moves.json')
        return $target
    }
    CheckIdle
    $oldMapPath=[IO.Path]::GetFullPath($plan.old_map.path)
    if ($oldMapPath -ne (Join-Path $taskProject 'Content\GameMaps\Design\L_PowerTheme20261004_Subject.umap')) { throw 'Unexpected canonical map' }
    $oldMapArchive=ArchiveFile $oldMapPath $plan.old_map.sha256 'Content\GameMaps\Design\L_PowerTheme20261004_Subject.umap'
    SaveJson @{stage='old_map_archived';archive_root=$archiveRoot;old_map_archive=$oldMapArchive;old_map_sha256=$plan.old_map.sha256} (Join-Path $receipts 'publication-archive.json')
    try { RunStage 'publish_current_map.py' } catch {
        $failure=$_
        CheckIdle
        if (Test-Path -LiteralPath $oldMapPath) {
            ArchiveFile $oldMapPath (HashOf $oldMapPath) 'FailedPublication\L_PowerTheme20261004_Subject.umap' | Out-Null
        }
        Copy-Item -LiteralPath $oldMapArchive -Destination $oldMapPath
        throw $failure
    }
    $published=Get-Content -LiteralPath (Join-Path $receipts 'publication.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($published.stage -ne 'canonical_map_saved' -or (HashOf $oldMapPath) -ne $published.map_sha256) { throw 'Canonical map save receipt/hash mismatch; preserve archives and all remaining assets' }
    CheckIdle
    foreach ($item in $audit.retire_assets) {
        $path=[IO.Path]::GetFullPath($item.path)
        $oldPrefix=$taskProject+'\Content\Dungeons\PowerTheme20261004\'
        if (-not $path.StartsWith($oldPrefix,[StringComparison]::OrdinalIgnoreCase) -or $path.StartsWith(($oldPrefix+'RefineV2\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Old asset candidate outside exact scope' }
        ArchiveFile $path $item.sha256 $path.Substring($taskProject.Length+1) | Out-Null
    }
    $oldSource=[IO.Path]::GetFullPath((Join-Path $taskProject 'SourceAssets\DungeonPowerTheme20261004'))
    if ($oldSource -ne 'D:\FPS3D\FPSGAME\SourceAssets\DungeonPowerTheme20261004') { throw 'Unexpected source archive target' }
    $oldSourceArchived=$false
    if (@($audit.retained_assets).Count -eq 0 -and (Test-Path -LiteralPath $oldSource)) {
        if (@(Get-ChildItem -LiteralPath $oldSource -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw 'Preserve source containing reparse points' }
        $sourceHashes=@(Get-ChildItem -LiteralPath $oldSource -File -Recurse | ForEach-Object { @{relative=$_.FullName.Substring($oldSource.Length+1);sha256=(HashOf $_.FullName);bytes=$_.Length} })
        SaveJson $sourceHashes (Join-Path $archiveRoot 'old-source-hashes.json')
        $sourceArchive=Join-Path $archiveRoot 'SourceAssets\DungeonPowerTheme20261004'
        New-Item -ItemType Directory -Force -Path (Split-Path $sourceArchive -Parent) | Out-Null
        Move-Item -LiteralPath $oldSource -Destination $sourceArchive
        $moves.Add([pscustomobject]@{source=$oldSource;archive=$sourceArchive;kind='directory';hash_manifest='old-source-hashes.json'})
        $oldSourceArchived=$true
    }
    foreach ($leaf in @('Meshes','Materials','Textures')) {
        $emptyFolder=[IO.Path]::GetFullPath((Join-Path $taskProject ('Content\Dungeons\PowerTheme20261004\'+$leaf)))
        if ($emptyFolder -ne ($taskProject+'\Content\Dungeons\PowerTheme20261004\'+$leaf)) { throw 'Unexpected empty folder scope' }
        if ((Test-Path -LiteralPath $emptyFolder) -and @(Get-ChildItem -LiteralPath $emptyFolder -Force).Count -eq 0) { Remove-Item -LiteralPath $emptyFolder -Force }
    }
    $staging=[IO.Path]::GetFullPath($plan.staging_map_file)
    if ($staging -ne (Join-Path $taskProject 'Content\GameMaps\Design\L_PowerTheme20261004_RefineV2_Subject.umap')) { throw 'Unexpected staging map' }
    ArchiveFile $staging $audit.staging_map_sha256 'Staging\L_PowerTheme20261004_RefineV2_Subject.umap' | Out-Null
    SaveJson @($moves.ToArray()) (Join-Path $archiveRoot 'moves.json')
    Copy-Item -LiteralPath (Join-Path $taskRoot 'Scripts\Restore-Previous.ps1') -Destination (Join-Path $archiveRoot 'Restore-Previous.ps1')
    $record=@{stage='published_and_old_theme_archived';archive_root=$archiveRoot;canonical_map=$plan.canonical_map;map_sha256=(HashOf $oldMapPath);retired_assets=@($audit.retire_assets).Count;retained_assets=@($audit.retained_assets);old_source_archived=$oldSourceArchived;staging_map_archived=$true;permanent_delete=$false;restore_script=(Join-Path $archiveRoot 'Restore-Previous.ps1');tests_run=$false;rendered=$false;game_run=$false}
    SaveJson $record (Join-Path $receipts 'publication-archive.json')
    SaveJson $record (Join-Path $archiveRoot 'publication.json')
    Write-Output ('POWER_THEME_PUBLICATION_COMPLETE '+$plan.canonical_map)
} finally { if ($held) { $taskGate.ReleaseMutex() };$taskGate.Dispose() }
