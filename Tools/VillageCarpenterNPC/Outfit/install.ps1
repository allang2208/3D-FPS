param([switch]$InstallSaved)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$out = Join-Path $project 'SourceAssets/VillageCarpenterNPC/Outfit'
$hostDir = Join-Path $env:TEMP 'FPSGAME_CarpenterWorkwearAuthor'
$hostProject = Join-Path $hostDir 'CarpenterWorkwear.uproject'
$content = Join-Path $hostDir 'Content'
$characterDir = Join-Path $content 'Characters'
$relDir = 'Characters/VillageCarpenterNPC/Outfit'
$sourceHost = Join-Path $project 'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit/Host'

New-Item -ItemType Directory -Force -Path $characterDir,(Join-Path $content $relDir) | Out-Null
Copy-Item -LiteralPath "$sourceHost/SmithBody.uproject" -Destination $hostProject
$references = @{
    'AsianMale_Jason' = "$project/Content/AsianMale_Jason"
    'Characters/ModularOutfit20260924' = "$sourceHost/Content/Characters/ModularOutfit20260924"
    'Characters/VillageBlacksmithNPC20261118' = "$project/Content/Characters/VillageBlacksmithNPC20261118"
}
foreach ($pair in $references.GetEnumerator()) {
    $destination = Join-Path $content $pair.Key
    if (!(Test-Path -LiteralPath $destination)) {
        New-Item -ItemType Junction -Path $destination -Target $pair.Value | Out-Null
    }
}
$cmdlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$env:UE_SKIP_UBT_SDK_SETUP = '1'
if (!$InstallSaved) {
    & $cmdlet $hostProject -run=pythonscript "-script=$PSScriptRoot/save_workwear.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$out/save.log" *> "$out/save.console.log"
}
$log = Get-Content -LiteralPath "$out/save.log" -Raw
if ($log -notmatch 'CARPENTER_WORKWEAR_SAVED /Game/Characters/VillageCarpenterNPC/Outfit/SK_Carpenter_Workwear' -or
    $log -notmatch 'PythonScriptCommandlet_0 finished execution \(result 0\)') {
    throw "Carpenter asset save did not complete. See $out/save.log"
}

$receipt = Get-Content -LiteralPath "$out/saved.json" -Raw | ConvertFrom-Json
$old = @{}
if (Test-Path -LiteralPath "$out/installed.json") {
    $previous = Get-Content -LiteralPath "$out/installed.json" -Raw | ConvertFrom-Json
    foreach ($record in $previous.files) { $old[$record.file] = $record.sha256 }
}
$guard = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $guard.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $records = @()
    foreach ($package in $receipt.packages) {
        if (!$package.StartsWith("/Game/$relDir/")) {throw "Unexpected package $package"}
        $relative = $package.Substring(6) + '.uasset'
        $src = Join-Path $content $relative
        $dst = Join-Path "$project/Content" $relative
        $hash = (Get-FileHash -LiteralPath $src).Hash
        if (Test-Path -LiteralPath $dst) {
            $current = (Get-FileHash -LiteralPath $dst).Hash
            if ($current -ne $hash -and $current -ne $old[$relative]) {
                throw "Carpenter asset already has independently modified contents: $relative"
            }
        }
        $records += [PSCustomObject]@{file=$relative; sha256=$hash}
    }
    foreach ($record in $records) {
        $src = Join-Path $content $record.file
        $dst = Join-Path "$project/Content" $record.file
        if ((Test-Path -LiteralPath $dst) -and (Get-FileHash -LiteralPath $dst).Hash -eq $record.sha256) {continue}
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        $temp = "$dst.carpenter.tmp"
        [IO.File]::Copy($src, $temp, $true)
        [IO.File]::Move($temp, $dst, $true)
    }
    [PSCustomObject]@{outfit=$receipt.outfit; files=$records} | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath "$out/installed.json" -Encoding utf8
    Write-Output ("Installed {0} carpenter packages including {1}." -f $records.Count, $receipt.outfit)
} finally {
    if ($held) { $guard.ReleaseMutex() }
    $guard.Dispose()
}
