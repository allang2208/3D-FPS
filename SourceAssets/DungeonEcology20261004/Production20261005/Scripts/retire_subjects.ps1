param()
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskSource=Split-Path $taskRoot -Parent
$taskProject=(Resolve-Path -LiteralPath 'D:\FPS3D\FPSGAME').Path
$taskTrash=[IO.Path]::GetFullPath((Join-Path $taskProject 'trash\ecology-subjects-promoted-20261005'))
if (-not $taskTrash.StartsWith($taskProject+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Invalid archive directory'}
$taskReceiptPath=Join-Path $taskRoot 'Receipts/install.json'
$taskReceipt=Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
if ($taskReceipt.stage -ne 'map_saved') {throw 'Preserve subjects until production is saved'}
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {try {$taskHeld=$taskMutex.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like '*FPSGAME*'})
    if ($taskEditors.Count -gt 0) {throw 'Preserve loaded assets; retire through the existing editor or after it closes'}
    New-Item -ItemType Directory -Path $taskTrash -Force | Out-Null
    $taskEntries=@()
    foreach ($taskName in @('L_EcoNursery_Subject','L_EcoHydroponics_Subject','L_EcoBiosphere_Subject','L_Ecology_Theme_Subject')) {
        $taskPackage='/Game/GameMaps/Design/'+$taskName
        if (@($taskReceipt.subject_external_referencers.$taskPackage).Count -gt 0) {throw 'Subject still has external users'}
        foreach ($taskSuffix in @('.umap','.uexp','.ubulk','.uptnl','.uasset')) {
            $taskRel='Content\GameMaps\Design\'+$taskName+$taskSuffix
            $taskFrom=[IO.Path]::GetFullPath((Join-Path $taskProject $taskRel))
            if (-not $taskFrom.StartsWith($taskProject+'\Content\GameMaps\Design\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Invalid subject source'}
            if (-not (Test-Path -LiteralPath $taskFrom -PathType Leaf)) {continue}
            $taskTo=[IO.Path]::GetFullPath((Join-Path $taskTrash $taskRel))
            if (-not $taskTo.StartsWith($taskTrash+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Invalid archive target'}
            if (Test-Path -LiteralPath $taskTo) {throw 'Preserve existing archive'}
            $taskHash=(Get-FileHash -LiteralPath $taskFrom -Algorithm SHA256).Hash.ToLowerInvariant()
            $taskSize=(Get-Item -LiteralPath $taskFrom).Length
            New-Item -ItemType Directory -Path (Split-Path $taskTo -Parent) -Force | Out-Null
            Move-Item -LiteralPath $taskFrom -Destination $taskTo
            $taskEntries+=@{original=$taskRel;archived=$taskTo;bytes=$taskSize;sha256=$taskHash;reason='Accepted ecology is now referenced by L_Dungeon_Randomized; recoverable subject retirement.'}
        }
    }
    $taskManifest=@{files=$taskEntries;replacement='/Game/GameMaps/L_Dungeon_Randomized';shared_assets_preserved=$true;author_sources_preserved=$true}
    [IO.File]::WriteAllText((Join-Path $taskTrash 'manifest.json'),($taskManifest | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    $taskReceipt.samples_retirement='archived'
    $taskReceipt | Add-Member -Force -NotePropertyName subject_archive -NotePropertyValue $taskTrash
    [IO.File]::WriteAllText($taskReceiptPath,($taskReceipt | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    $taskConfigPath=Join-Path $taskSource 'Config/room.json'
    $taskConfig=Get-Content -LiteralPath $taskConfigPath -Raw | ConvertFrom-Json
    $taskConfig.subject_status='archived'
    [IO.File]::WriteAllText($taskConfigPath,($taskConfig | ConvertTo-Json -Depth 100),[Text.UTF8Encoding]::new($false))
    Write-Output ('ECOLOGY_SUBJECTS_ARCHIVED files='+$taskEntries.Count)
} finally {
    if ($taskHeld) {$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}