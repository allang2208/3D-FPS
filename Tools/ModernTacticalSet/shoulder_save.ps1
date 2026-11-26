param([string]$ManifestPath)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$hostProject = Join-Path $PSScriptRoot 'ShoulderFitHost/ShoulderFit.uproject'
$mountRoot = Join-Path $PSScriptRoot 'ShoulderFitHost/Content'
New-Item -ItemType Directory -Force -Path $mountRoot | Out-Null
foreach ($name in @('AsianMale_Jason','Characters','Items','Weapons')) {
    $link = Join-Path $mountRoot $name
    $target = (Resolve-Path (Join-Path $projectRoot ('Content/'+$name))).Path
    if (!(Test-Path -LiteralPath $link)) {
        New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    }
    if ((Get-Item -LiteralPath $link).Target -ne $target) { throw "Unexpected content mount at $link" }
}
$output = Join-Path $projectRoot 'SourceAssets/ModernTacticalSet20261113/ShoulderFit20261118'
$engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
try {
    $manifests = if ($ManifestPath) { Get-Item -LiteralPath $ManifestPath } else {
        foreach ($folder in @($output,(Join-Path $output 'Queued'))) {
            if (Test-Path -LiteralPath $folder) {
                Get-ChildItem -LiteralPath $folder -Filter '*.txt' | Where-Object Name -Match '^(Jason|Kaitlin)-\d+\.txt$'
            }
        }
    }
    foreach ($manifest in $manifests) {
        $rig = $manifest.BaseName.Split('-')[0]
        $all = @(Get-Content -LiteralPath $manifest.FullName)
        $todo = @()
        foreach ($source in $all) {
            $dest = $source.Replace('/CombatShirtR4/','/ShoulderFit20261118/')
            $disk = Join-Path $projectRoot ('Content/'+$dest.Substring(6)+'.uasset')
            if (!(Test-Path -LiteralPath $disk)) { $todo += $source; continue }
            if (!((Get-ChildItem -LiteralPath $output -Filter ($rig+'-*-save*.log')) | Select-String -SimpleMatch "TS01_BODY_SAVED $dest ")) {
                throw "Preserving an unreceipted asset at $disk"
            }
        }
        if (!$todo.Count) { continue }
        $runList = Join-Path $output ($manifest.BaseName+'.remaining')
        $todo | Set-Content -LiteralPath $runList -Encoding utf8NoBOM
        $log = Join-Path $output ($manifest.BaseName+'-save-'+(Get-Date -Format 'HHmmss-fff')+'.log')
        $held = $false
        try {
            try { $held = $gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
            & $engine $hostProject '/Engine/Maps/Entry' '-run=RefitShoulder' "-Work=$output" "-List=$runList" "-Rig=$rig" '-NullRHI' '-unattended' '-nop4' '-nosound' '-nosplash' '-Multiprocess' '-AssetGatherAll=false' '-asyncskinnedassetcompilation=0' "-abslog=$log" *> "$log.stdout"
            if ($LASTEXITCODE -ne 0) { throw "Shoulder save exited $LASTEXITCODE, see $log" }
        } finally { if ($held) { $gate.ReleaseMutex() } }
        Write-Output "Saved $($manifest.BaseName)"
    }
} finally { $gate.Dispose() }
