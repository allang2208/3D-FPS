$ErrorActionPreference = 'Stop'
$project = (Resolve-Path "$PSScriptRoot/../..").Path
$production = (Get-Item "$project/SourceAssets/VillageGunsmith").Target
$stage = Join-Path $production 'Host'
$engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$content = Join-Path $stage 'Content'
$descriptor = Join-Path $stage 'GunsmithAuthoring.uproject'
New-Item -ItemType Directory -Force -Path "$content/Characters/VillageGunsmith","$stage/Config" | Out-Null
foreach ($mount in @('AsianMale_Jason','Characters/VillageBlacksmithNPC20261118')) {
    if (!(Test-Path -LiteralPath "$content/$mount")) {
        New-Item -ItemType Junction -Path "$content/$mount" -Target "$project/Content/$mount" | Out-Null
    }
}
$plugins = (Get-Content "$project/SourceAssets/JasonStrong20261117/AuthoringHost/JasonAuthoring.uproject" -Raw | ConvertFrom-Json).Plugins
@{FileVersion=3; EngineAssociation='5.8'; Plugins=$plugins} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $descriptor -Encoding ascii
@'
[/Script/Engine.RendererSettings]
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
'@ | Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding ascii
if (!(Test-Path "$stage/saved.json")) {
    & $engine $descriptor -run=pythonscript "-script=$PSScriptRoot/import_head.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache' '-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen' '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT' "-abslog=$stage/import.log" *> "$stage/console.log"
    if (!(Test-Path "$stage/saved.json")) { throw "Gunsmith import failed ($LASTEXITCODE), see $stage/import.log" }
}
$receipt = Get-Content "$stage/saved.json" -Raw | ConvertFrom-Json
$prefix = '/Game/Characters/VillageGunsmith/'
$parent = (Resolve-Path "$project/Content/Characters").Path
$target = Join-Path $parent 'VillageGunsmith'
if (Test-Path "$production/installed.json") { return }
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    if (Test-Path -LiteralPath $target) { throw "A gunsmith already occupies $target." }
    $fresh = [IO.Path]::GetFullPath((Join-Path $parent ('.Gunsmith-' + [Guid]::NewGuid().ToString('N'))))
    foreach ($pkg in $receipt.packages) {
        if (!$pkg.StartsWith($prefix) -or $pkg.Contains('..')) { throw "Unexpected package $pkg" }
        $rel = $pkg.Substring($prefix.Length)
        $folder = [IO.Path]::GetDirectoryName("$fresh/$rel.uasset")
        [IO.Directory]::CreateDirectory($folder) | Out-Null
        foreach ($ext in @('.uasset','.ubulk','.uexp','.uptnl')) {
            $src = "$content/Characters/VillageGunsmith/$rel$ext"
            if ($ext -eq '.uasset' -or (Test-Path -LiteralPath $src)) {
                [IO.File]::Copy($src, "$fresh/$rel$ext", $false)
            }
        }
    }
    if ((Split-Path -Parent $fresh) -ne $parent -or (Split-Path -Parent $target) -ne $parent) { throw 'Unexpected publishing directory' }
    [IO.Directory]::Move($fresh, $target)
    Copy-Item "$stage/saved.json" "$production/installed.json"
    Write-Output "Installed $($receipt.packages.Count) packages, $($receipt.mesh)"
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
