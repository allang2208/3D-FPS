$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    Write-Output 'Waiting to save the three M870 meshes and build in one asset batch.'
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'The UE asset batch gate did not become available.'}
    Write-Output 'M870 final asset batch acquired.'
    & (Join-Path $PSScriptRoot 'run_asset.ps1') -Script 'import_assets.py' *> (Join-Path $PSScriptRoot 'import_console.log')
    if($LASTEXITCODE -ne 0){throw 'M870 tactical import failed.'}
    $receipt=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'import_receipt.json') -Raw | ConvertFrom-Json
    if(-not $receipt.completed){throw 'The M870 mesh save did not complete.'}
    & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' *> (Join-Path $PSScriptRoot 'build_editor.log')
    if($LASTEXITCODE -ne 0){throw 'M870 source build did not succeed.'}
    Write-Output 'M870 tactical meshes saved and Editor build complete.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
