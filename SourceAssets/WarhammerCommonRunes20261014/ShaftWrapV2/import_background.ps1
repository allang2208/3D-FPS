$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$projectRoot = 'D:\FPS3D\FPSGAME'
$package = "$projectRoot\Content\Weapons\SteelWarhammer20261014\Runes\ShaftWrapV2\M_SilverRuneSurface_WarhammerShaftV2.uasset"
$gui = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
if ($gui -and (Test-Path -LiteralPath $package)) {
    $outputFile = Join-Path $taskRoot ('bridge-'+[Guid]::NewGuid().ToString('N')+'.txt')
    & "$projectRoot\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript "$taskRoot\install_material.py" -OutputFile $outputFile -MaxOutputChars 2500 -QueueWaitSeconds 600 -RequestTimeoutSeconds 300
    exit $LASTEXITCODE
}
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    $started = [DateTime]::UtcNow
    while (-not $held -and ([DateTime]::UtcNow-$started).TotalMinutes -lt 10) {
        try { $held = $gate.WaitOne(1000) } catch [Threading.AbandonedMutexException] { $held = $true }
    }
    if (-not $held) { throw 'Shared asset batch is occupied; material not changed.' }
    $gui = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
    if ($gui -and (Test-Path -LiteralPath $package)) { throw 'Existing material may be loaded; use its editor bridge.' }
    $buildWaitStarted = [DateTime]::UtcNow
    do {
        $building = Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor' }
        if ($building) {
            if (([DateTime]::UtcNow-$buildWaitStarted).TotalMinutes -ge 10) { throw 'Native build remains active; material not changed.' }
            Start-Sleep -Seconds 3
        }
    } while ($building)
    $gui = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
    if ($gui -and (Test-Path -LiteralPath $package)) { throw 'Existing material may be loaded; use its editor bridge.' }
    if ((Test-Path -LiteralPath $package) -and -not (Test-Path -LiteralPath "$taskRoot\import_receipt.json")) { throw 'Existing unowned target package; preserve it.' }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$projectRoot\FPSGAME.uproject" -run=PythonScript "-script=$taskRoot\install_material.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$taskRoot\import-engine.log" *> "$taskRoot\import-console.log"
    $resultCode = $LASTEXITCODE
    @{exit_code=$resultCode;game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot\commandlet_receipt.json" -Encoding UTF8
    exit $resultCode
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
