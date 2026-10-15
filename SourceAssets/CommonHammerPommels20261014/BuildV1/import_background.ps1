param()
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\FPS3D\FPSGAME\SourceAssets\CommonHammerPommels20261014\BuildV1'
$projectRoot = 'D:\FPS3D\FPSGAME'
$gui = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
if ($gui) {
    $bridgeOutput = Join-Path $taskRoot ('bridge-import-'+[Guid]::NewGuid().ToString('N')+'.txt')
    & "$projectRoot\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript "$taskRoot\import_pommels.py" -OutputFile $bridgeOutput -MaxOutputChars 2500 -RequestTimeoutSeconds 300
    exit $LASTEXITCODE
}
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    $queueStarted = [DateTime]::UtcNow
    $nextNotice = $queueStarted.AddSeconds(60)
    while (-not $held -and ([DateTime]::UtcNow - $queueStarted).TotalMinutes -lt 15) {
        try { $held = $gate.WaitOne(1000) } catch [Threading.AbandonedMutexException] { $held = $true }
        if (-not $held -and [DateTime]::UtcNow -ge $nextNotice) {
            Write-Output 'Waiting for the shared asset batch mutex; no packages modified.'
            $nextNotice = [DateTime]::UtcNow.AddSeconds(60)
        }
    }
    if (-not $held) { throw 'Asset batch stayed occupied for 15 minutes; import not started.' }
    $gui = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
    if ($gui) { throw 'Editor opened during scheduling; use the current editor bridge.' }
    $editorBuild = Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor' }
    if ($editorBuild) { throw 'Editor native build is active; defer commandlet.' }
    # This batch saves only new packages; shared factory/head/seat materials are read-only.
    $ownedPartial = @()
    if (Test-Path -LiteralPath "$taskRoot\import_receipt.json") {
        $receipt = Get-Content -Raw -LiteralPath "$taskRoot\import_receipt.json" | ConvertFrom-Json
        if ($receipt.complete) { Write-Output 'Import already complete.'; exit 0 }
        $ownedPartial = @($receipt.assets | ForEach-Object { (($_.Split('.')[0] -replace '^/Game/','')+'.uasset') })
    }
    $packages = @('Weapons/CommonHammerPommels20261014/BuildV1/Materials/M_CommonHammerPommelTurned.uasset')
    foreach ($channel in @('Normal','ORM')) {
        $packages += 'Weapons/CommonHammerPommels20261014/BuildV1/Textures/T_HammerPommelTurned_'+$channel+'.uasset'
    }
    $exports = Get-Content -Raw -LiteralPath "$taskRoot\exports.json" | ConvertFrom-Json
    foreach ($row in $exports.parts) {
        $packages += 'Weapons/CommonHammerPommels20261014/BuildV1/'+$row.mesh+'.uasset'
        $packages += 'ColdSteelData/AttachmentIcons20260913/pommel_'+$row.id+'.uasset'
    }
    foreach ($package in $packages) {
        if ((Test-Path -LiteralPath (Join-Path "$projectRoot\Content" $package)) -and $package -notin $ownedPartial) {
            throw ('Existing package is not a partial save from this batch: '+$package)
        }
    }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$projectRoot\FPSGAME.uproject" -run=PythonScript "-script=$taskRoot\import_pommels.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$taskRoot\import-engine.log" *> "$taskRoot\import-console.log"
    $resultCode = $LASTEXITCODE
    @{exit_code=$resultCode;fresh_packages_only=$true;game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot\commandlet_receipt.json" -Encoding UTF8
    exit $resultCode
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
