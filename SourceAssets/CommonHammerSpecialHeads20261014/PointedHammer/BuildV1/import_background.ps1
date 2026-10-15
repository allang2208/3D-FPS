$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$projectRoot = 'D:\FPS3D\FPSGAME'
$targetFiles = @(
    "$projectRoot\Content\Weapons\CommonHammerSpecialHeads20261014\PointedHammer\BuildV1\SM_CommonHammerHeads_pointed_hammer_V1.uasset",
    "$projectRoot\Content\ColdSteelData\AttachmentIcons20260913\hammer_heads_pointed_hammer.uasset"
)
$gui = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
$existing = @($targetFiles | Where-Object { Test-Path -LiteralPath $_ })
if ($gui -and $existing.Count -gt 0) {
    $outputFile = Join-Path $taskRoot ('bridge-'+[Guid]::NewGuid().ToString('N')+'.txt')
    & "$projectRoot\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript "$taskRoot\import_pointed_hammer.py" -OutputFile $outputFile -MaxOutputChars 2500 -QueueWaitSeconds 600 -RequestTimeoutSeconds 300
    exit $LASTEXITCODE
}
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    $started = [DateTime]::UtcNow
    while (-not $held -and ([DateTime]::UtcNow-$started).TotalMinutes -lt 10) {
        try { $held = $gate.WaitOne(1000) } catch [Threading.AbandonedMutexException] { $held = $true }
    }
    if (-not $held) { throw 'Shared asset batch is occupied; targets not changed.' }
    $buildWaitStarted = [DateTime]::UtcNow
    do {
        $building = Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor' }
        if ($building) {
            if (([DateTime]::UtcNow-$buildWaitStarted).TotalMinutes -ge 10) { throw 'Editor build remains active; import deferred.' }
            Start-Sleep -Seconds 3
        }
    } while ($building)
    $gui = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
    $existing = @($targetFiles | Where-Object { Test-Path -LiteralPath $_ })
    if ($gui -and $existing.Count -gt 0) { throw 'Existing target may be loaded; use its editor bridge.' }
    if ($existing.Count -gt 0 -and -not (Test-Path -LiteralPath "$taskRoot\import_receipt.json")) { throw 'Existing unowned target package; preserve it.' }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$projectRoot\FPSGAME.uproject" -run=PythonScript "-script=$taskRoot\import_pointed_hammer.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess "-abslog=$taskRoot\import-engine.log" *> "$taskRoot\import-console.log"
    $resultCode = $LASTEXITCODE
    @{exit_code=$resultCode;game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot\commandlet_receipt.json" -Encoding UTF8
    exit $resultCode
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
