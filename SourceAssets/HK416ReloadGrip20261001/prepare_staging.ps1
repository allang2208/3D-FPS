$ErrorActionPreference = 'Stop'
$hkProject = 'D:\FPS3D\FPSGAME'
$hkAuthor = Join-Path $hkProject 'SourceAssets\HK416ReloadGrip20261001'
$hkStage = Join-Path $hkAuthor 'PackageStaging'
if (Test-Path -LiteralPath $hkStage) { throw 'Staging directory already exists; preserve it.' }
[IO.Directory]::CreateDirectory($hkStage) | Out-Null
$hkInputs = Get-Content -LiteralPath (Join-Path $hkAuthor 'inputs.json') -Raw | ConvertFrom-Json
$hkTargets = @($hkInputs.clips.psobject.Properties.Name | ForEach-Object { $_.Substring(6) + '.uasset' })
$hkTargets += @('vertical','canted','prism','angled','drum' | ForEach-Object { 'Weapons/AnimationProfiles20261001/ue_hk416/DA_' + $_ + '.uasset' })
function Copy-HkOverlay([string]$hkRelative) {
    $hkFrom = Join-Path (Join-Path $hkProject 'Content') $hkRelative
    $hkTo = Join-Path (Join-Path $hkStage 'Content') $hkRelative
    [IO.Directory]::CreateDirectory($hkTo) | Out-Null
    foreach ($hkEntry in Get-ChildItem -LiteralPath $hkFrom) {
        $hkChild = if ($hkRelative) { $hkRelative.Replace('\','/') + '/' + $hkEntry.Name } else { $hkEntry.Name }
        $hkOutput = Join-Path $hkTo $hkEntry.Name
        if ($hkEntry.PSIsContainer) {
            $hkPrefix = $hkChild + '/'
            $hkAffected = @($hkTargets | Where-Object { $_.StartsWith($hkPrefix,[StringComparison]::OrdinalIgnoreCase) }).Count -gt 0
            if ($hkAffected) { Copy-HkOverlay $hkChild }
            else { New-Item -ItemType Junction -Path $hkOutput -Target $hkEntry.FullName | Out-Null }
        } else { Copy-Item -LiteralPath $hkEntry.FullName -Destination $hkOutput }
    }
}
Copy-HkOverlay ''
Copy-Item -LiteralPath (Join-Path $hkProject 'FPSGAME.uproject') -Destination (Join-Path $hkStage 'FPSGAME.uproject')
Copy-Item -LiteralPath (Join-Path $hkProject 'Config') -Destination (Join-Path $hkStage 'Config') -Recurse
foreach ($hkFolder in @('Binaries','Plugins')) {
    New-Item -ItemType Junction -Path (Join-Path $hkStage $hkFolder) -Target (Join-Path $hkProject $hkFolder) | Out-Null
}
$hkManifest = @{}
foreach ($hkTarget in $hkTargets) {
    $hkOriginal = Join-Path (Join-Path $hkProject 'Content') $hkTarget
    $hkCopy = Join-Path (Join-Path $hkStage 'Content') $hkTarget
    $hkManifest[$hkTarget] = @{ original_sha256=(Get-FileHash -LiteralPath $hkOriginal -Algorithm SHA256).Hash.ToLower(); staged_file=$hkCopy }
}
@{project=$hkProject;staging=$hkStage;targets=$hkManifest;runtime_tested=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $hkAuthor 'staging.json') -Encoding UTF8
Write-Output ('HK416_ISOLATED_PACKAGE_STAGING_READY ' + $hkTargets.Count)
