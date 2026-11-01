$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for the UE batch gate before the necessary native build.'
    try { $held=$gate.WaitOne(1200000) } catch [Threading.AbandonedMutexException] { $held=$true }
    if (-not $held) { throw 'UE batch remains occupied; native build remains pending.' }
    & "$projectRoot/Tools/Build/Build-Editor.ps1"
    if ($LASTEXITCODE -ne 0) { throw 'Native editor build failed.' }
    [IO.File]::WriteAllText("$projectRoot/SourceAssets/M24IronSights20261027/build_receipt.json",('{"editor_build":"succeeded","finished_local":"'+(Get-Date -Format o)+'","runtime_tested":false}'))
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
