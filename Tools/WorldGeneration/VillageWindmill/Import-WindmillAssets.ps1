param(
    [string]$Art = 'F:/FPSGAMEData/ArtProduction/HillsVillageWindmill/GameR1',
    [string]$Engine = 'E:/Program Files (x86)/UE_5.8'
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$engineCmd = Join-Path $Engine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$run = Join-Path $Art ('ImportHost/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$stage = Join-Path $run 'Host'
$cache = 'F:/FPSGAMEData/Caches/DerivedDataCache'
New-Item -ItemType Directory -Path "$stage/Config" -Force | Out-Null
@{
    FileVersion = 3
    EngineAssociation = '5.8'
    Plugins = @(@{Name='PythonScriptPlugin';Enabled=$true}, @{Name='EditorScriptingUtilities';Enabled=$true})
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$stage/WindmillAuthor.uproject" -Encoding utf8NoBOM
@'
[/Script/Engine.RendererSettings]
r.VirtualTextures=True
r.AllowStaticLighting=False
[ConsoleVariables]
Interchange.FeatureFlags.Import.FBX=False
'@ | Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8NoBOM
$arguments = @(
    ('"'+$stage+'/WindmillAuthor.uproject"'), '/Engine/Maps/Entry', '-run=pythonscript',
    ('-script="'+$PSScriptRoot+'/import_windmill_assets.py"'), '-unattended', '-NullRHI',
    '-nosplash', '-nosound', '-nop4', '-Multiprocess', '-AssetGatherAll=false',
    '-NoAssetRegistryCacheWrite', ('-LocalDataCachePath='+$cache),
    ('-ZenDataPath='+$cache+'/Zen'),
    ('-ini:Engine:[VirtualTextureChunkDDCCache]:Path='+$cache+'/VT'), ('-abslog="'+$run+'/engine.log"')
)
$env:WINDMILL_PROJECT = $project
$env:WINDMILL_ART = $Art
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$catalog = Get-Content -Raw -LiteralPath "$project/SourceAssets/HillsVillageWindmill/ComponentsR2/catalog.json" | ConvertFrom-Json
Write-Output "Windmill import log directory $run"
while (-not (Test-Path -LiteralPath "$Art/Exchange/geometry.json" -PathType Leaf)) { Start-Sleep -Seconds 5 }
foreach ($row in $catalog) {
    if (-not (Test-Path -LiteralPath "$Art/Exchange/SM_Windmill_$($row.id).fbx" -PathType Leaf)) {
        throw "Missing completed geometry $($row.id)"
    }
}
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    # Unreal can keep the package it is replacing open while another asset is
    # being built. Give this commandlet its own writable copy of the mill kit.
    $live = Join-Path $project 'Content'
    $private = Join-Path $stage 'Content'
    foreach ($branch in 'WorldGeneration','TemperateHills','VillageWindmill') {
        New-Item -ItemType Directory -Force -Path $private | Out-Null
        foreach ($sibling in Get-ChildItem -LiteralPath $live) {
            if ($sibling.Name -eq $branch) { continue }
            $link = Join-Path $private $sibling.Name
            if ($sibling.PSIsContainer) {
                New-Item -ItemType Junction -Path $link -Target $sibling.FullName | Out-Null
            } else {
                Copy-Item -LiteralPath $sibling.FullName -Destination $link
            }
        }
        $live = Join-Path $live $branch
        $private = Join-Path $private $branch
    }
    New-Item -ItemType Directory -Force -Path $private | Out-Null
    $baseline = @{}
    if (Test-Path -LiteralPath $live) {
        foreach ($f in Get-ChildItem -LiteralPath $live -File -Recurse) {
            $rel = [IO.Path]::GetRelativePath($live,$f.FullName)
            $copy = Join-Path $private $rel
            New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($copy)) | Out-Null
            Copy-Item -LiteralPath $f.FullName -Destination $copy
            $baseline[$rel] = (Get-FileHash -LiteralPath $copy).Hash
        }
    }
    $env:WINDMILL_IMPORT_RECEIPT = Join-Path $run 'staged-import.json'
    if (Test-Path -LiteralPath "$Art/imported.json") {
        Copy-Item -LiteralPath "$Art/imported.json" -Destination $env:WINDMILL_IMPORT_RECEIPT
    }
    $proc = Start-Process -FilePath $engineCmd -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
    if ($proc.ExitCode -ne 0) { throw "Windmill import exited with $($proc.ExitCode). See $run/engine.log" }
    $receipt = Get-Content -Raw -LiteralPath $env:WINDMILL_IMPORT_RECEIPT | ConvertFrom-Json
    if (-not $receipt.complete -or @($receipt.saved.PSObject.Properties).Count -ne $catalog.Count) {
        throw "Windmill package saves did not finish. See $run/engine.log"
    }
    foreach ($f in Get-ChildItem -LiteralPath $private -File -Recurse) {
        $rel = [IO.Path]::GetRelativePath($private,$f.FullName)
        $digest = (Get-FileHash -LiteralPath $f.FullName).Hash
        if ($baseline[$rel] -eq $digest) { continue }
        $path = Join-Path $live $rel
        $folder = [IO.Path]::GetDirectoryName($path)
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        $old = if (Test-Path -LiteralPath $path) { (Get-FileHash -LiteralPath $path).Hash }
        if ($digest -eq $old) { continue }
        if ($baseline[$rel] -ne $old) { throw "Package changed since this import started: $path" }
        if ($old) {
            $previous = Join-Path "$run/Before" $rel
            New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($previous)) | Out-Null
            Copy-Item -LiteralPath $path -Destination $previous
        }
        $temp = Join-Path $folder ([guid]::NewGuid().ToString()+'.windmill-tmp')
        Copy-Item -LiteralPath $f.FullName -Destination $temp
        try {
            for ($attempt = 0; ; $attempt++) {
                $current = if (Test-Path -LiteralPath $path) { (Get-FileHash -LiteralPath $path).Hash }
                if ($current -ne $old) { throw "Package changed before publication: $path" }
                try { [IO.File]::Move($temp,$path,$true); break }
                catch [IO.IOException] { if($attempt -ge 12){throw}; Start-Sleep -Seconds 3 }
            }
        } finally {
            if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp }
        }
    }
    $tempReceipt = Join-Path $Art ('imported.'+[guid]::NewGuid().ToString()+'.tmp')
    Copy-Item -LiteralPath $env:WINDMILL_IMPORT_RECEIPT -Destination $tempReceipt
    [IO.File]::Move($tempReceipt,(Join-Path $Art 'imported.json'),$true)
    Write-Output "Saved $($catalog.Count) windmill meshes. $Art/imported.json"
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
