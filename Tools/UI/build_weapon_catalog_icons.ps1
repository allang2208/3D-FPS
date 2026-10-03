param(
    [string]$EngineRoot='E:/Program Files (x86)/UE_5.8',
    # Empty = the commandlet's own default definition list. A targeted re-shoot
    # passes names here so it works against the already-built binary, without a
    # native rebuild, because one process exports exactly one -Definition=.
    [string[]]$Definitions=@()
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$outputRoot=Join-Path $projectRoot 'SourceAssets/WeaponInventoryIcons20260913'
$engineCmd="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
New-Item -ItemType Directory -Force -Path (Join-Path $outputRoot 'before') | Out-Null
$script:Failed=@()

function Invoke-IconExport{
    param([string]$Definition,[string]$LogSuffix)
    $sourceIcon=Join-Path $projectRoot "Content/ColdSteelData/Icons/$Definition.png"
    $wroteBefore=Test-Path -LiteralPath $sourceIcon
    $beforeTime=if($wroteBefore){(Get-Item -LiteralPath $sourceIcon).LastWriteTime}else{$null}
    if($wroteBefore -and !(Test-Path -LiteralPath (Join-Path $outputRoot "before/$Definition.png"))){
        Copy-Item -LiteralPath $sourceIcon -Destination (Join-Path $outputRoot "before/$Definition.png")
    }
    $cmdArgs=@("$projectRoot/FPSGAME.uproject",'-run=ColdSteelWeaponIconCatalog','-AllowCommandletRendering','-NoTextureStreaming','-unattended','-nosplash','-RenderOffscreen')
    if($Definition){$cmdArgs+="-Definition=$Definition"}
    $cmdArgs+="-abslog=$outputRoot/export$LogSuffix.log"
    # A nonzero process exit can come from unrelated GameFeatureData or port
    # messages, so the written file timestamp is the result of record.
    & $engineCmd @cmdArgs *> "$outputRoot/export$LogSuffix-console.log"
    $exit=$LASTEXITCODE
    $fresh=$false;$dimension='-'
    if(Test-Path -LiteralPath $sourceIcon){
        $afterTime=(Get-Item -LiteralPath $sourceIcon).LastWriteTime
        $fresh=(-not $beforeTime) -or ($afterTime -gt $beforeTime)
        if($fresh){
            $bitmap=[System.Drawing.Bitmap]::FromFile($sourceIcon)
            $dimension='{0}x{1}' -f $bitmap.Width,$bitmap.Height
            $bitmap.Dispose()
        }
    }
    Write-Output ('ICON {0} written={1} size={2} exit={3} log=export{4}.log' -f $Definition,$fresh,$dimension,$exit,$LogSuffix)
    if(-not $fresh){$script:Failed+=$Definition}
}

if($Definitions.Count){
    # Split as well as bind: `pwsh -File` hands the comma list over as one string.
    foreach($definition in ($Definitions -join ',' -split ',' | Where-Object { $_ })){Invoke-IconExport -Definition $definition -LogSuffix "-$definition"}
}else{
    # Production image export only: no map, player profile, inventory audit or gameplay session.
    Invoke-IconExport -Definition '' -LogSuffix ''
}
if($script:Failed.Count){Write-Output ('ICONS_MISSING ' + ($script:Failed -join ','))}
exit $script:Failed.Count
