param()
$ErrorActionPreference='Stop'
$batchRoot='D:/FPS3D/FPSGAME/SourceAssets/IncineratorUpgrade20261027'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(55))
    if(!$held){Write-Output 'UE batch busy; asset not published.';exit 75}
    $src="$batchRoot/AssetHost/Content/Building/Incinerator20261027/S_IncineratorCombustionLoop.uasset"
    $dir='D:/FPS3D/FPSGAME/Content/Building/Incinerator20261027'
    $dst="$dir/S_IncineratorCombustionLoop.uasset"
    $hash=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
    if((Test-Path -LiteralPath $dst) -and (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash -ne $hash)
    {throw 'Destination differs; preserving existing asset'}
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst
    @{asset='/Game/Building/Incinerator20261027/S_IncineratorCombustionLoop';file=$dst;sha256=$hash;editorOpened=$false;auditioned=$false} |
        ConvertTo-Json | Set-Content -Encoding utf8 "$batchRoot/audio-published.json"
    Write-Output 'Saved combustion loop published.'
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
