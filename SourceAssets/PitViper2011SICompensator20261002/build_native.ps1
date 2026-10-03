$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    while ($true) {
        try { $taskHeld = $taskGate.WaitOne(15000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
        if (-not $taskHeld) { continue }
        $taskUe = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject'
        })
        $taskBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" | Where-Object {
            $_.Name -ne 'dotnet.exe' -or $_.CommandLine -match 'UnrealBuildTool'
        })
        if ($taskUe.Count -eq 0 -and $taskBuilds.Count -eq 0) { break }
        if (-not $taskReported) { Write-Output 'Existing editor, commandlet or build retained; SI native build waits automatically.'; $taskReported = $true }
        $taskGate.ReleaseMutex(); $taskHeld = $false
        Start-Sleep -Seconds 15
    }
    $taskResults = @()
    foreach ($taskTarget in @('FPSGAMEEditor', 'FPSGAME')) {
        $taskLog = Join-Path $taskProject "Saved/BuildEditor/pit-viper2011-si-$taskTarget-20261003.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -Module=FPSGAME -MaxParallelActions=4 "-Log=$taskLog"
        if ($LASTEXITCODE -ne 0) { throw "SI native build failed ($LASTEXITCODE): $taskLog" }
        $taskBinary = if ($taskTarget -eq 'FPSGAMEEditor') { 'Binaries/Win64/UnrealEditor-FPSGAME.dll' } else { 'Binaries/Win64/FPSGAME.exe' }
        $taskFile = Get-Item -LiteralPath (Join-Path $taskProject $taskBinary)
        $taskResults += @{ target=$taskTarget; status='Succeeded'; log=$taskLog; binary=$taskFile.FullName; bytes=$taskFile.Length; savedAtUtc=$taskFile.LastWriteTimeUtc.ToString('o') }
        @{ status='building'; targets=$taskResults; gameTested=$false } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
    }
    @{ status='Succeeded'; targets=$taskResults; gameTested=$false } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
