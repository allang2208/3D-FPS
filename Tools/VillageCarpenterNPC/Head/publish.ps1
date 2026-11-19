$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$work = Join-Path $project 'SourceAssets/VillageCarpenterNPC/Head'
$source = Join-Path $project 'SourceAssets/VillageCarpenterNPC/Meshy/HeadR1/Source'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$stage = Join-Path $work "AuthoringHost_$stamp"
$stock = Join-Path $project 'SourceAssets/VillageBlacksmithNPC20261118/HeadHair/AuthoringHost'
$prefix = '/Game/Characters/VillageCarpenterNPC/Head/'
$stageCharacters = Join-Path $stage 'Content/Characters'
New-Item -ItemType Directory -Path $stageCharacters -Force | Out-Null
Copy-Item -LiteralPath "$stock/SmithHead.uproject" -Destination "$stage/CarpenterHead.uproject"
foreach ($entry in @{
    "$stage/Content/AsianMale_Jason" = "$project/Content/AsianMale_Jason"
    "$stageCharacters/ModularOutfit20260924" = "$stock/Content/Characters/ModularOutfit20260924"
    "$stageCharacters/VillageBlacksmithNPC20261118" = "$project/Content/Characters/VillageBlacksmithNPC20261118"
}.GetEnumerator()) {
    New-Item -ItemType Junction -Path $entry.Key -Target $entry.Value | Out-Null
}
foreach ($entry in @{T_Carpenter_Head_BC='texture_0_base_color';T_Carpenter_Head_N='texture_0_normal'}.GetEnumerator()) {
    $name = $entry.Key
    Copy-Item -LiteralPath (Join-Path $source ($entry.Value+'.png')) -Destination "$work/$name.png" -Force
}
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$cmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $cmd "$stage/CarpenterHead.uproject" -run=pythonscript "-script=$PSScriptRoot/save_head.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$work/save_$stamp.log" *> "$work/console_$stamp.log"
if ($LASTEXITCODE -ne 0) { throw "Head authoring failed with return code $LASTEXITCODE in $stage" }
$saved = Get-Content -LiteralPath "$work/saved.json" -Raw | ConvertFrom-Json
$mutex = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $previous = @{}
    if (Test-Path -LiteralPath "$work/installed.json") {
        $last = Get-Content -LiteralPath "$work/installed.json" -Raw | ConvertFrom-Json
        foreach ($f in $last.files) { $previous[$f.pkg] = $f.hash }
    }
    $files = foreach ($pkg in $saved.packages) {
        if (-not $pkg.StartsWith($prefix, [StringComparison]::Ordinal)) { throw "Unexpected dependency $pkg" }
        $relative = 'Content/' + $pkg.Substring(6) + '.uasset'
        $from = Join-Path $stage $relative
        $dest = Join-Path $project $relative
        $hash = (Get-FileHash -LiteralPath $from).Hash
        if (Test-Path -LiteralPath $dest) {
            $current = (Get-FileHash -LiteralPath $dest).Hash
            if ($current -ne $hash -and $current -ne $previous[$pkg]) { throw "Destination has an independent change at $dest" }
        }
        [pscustomobject]@{pkg=$pkg;source=$from;destination=$dest;hash=$hash}
    }
    foreach ($file in ($files | Sort-Object { $_.pkg.EndsWith('/SK_Carpenter_Head') })) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $file.destination) -Force | Out-Null
        $pending = $file.destination + '.carpenter.tmp'
        [IO.File]::Copy($file.source, $pending, $true)
        [IO.File]::Move($pending, $file.destination, $true)
    }
    [ordered]@{head=$saved.head;skeleton=$saved.skeleton;files=$files} | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath "$work/installed.json" -Encoding utf8
    Write-Output ("Installed {0} carpenter head packages, including {1}" -f $files.Count,$saved.head)
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
