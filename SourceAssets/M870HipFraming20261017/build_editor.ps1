$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
$deadline = [DateTime]::UtcNow.AddMinutes(60)
$nextProgress = [DateTime]::UtcNow
$receipt = [ordered]@{
    started = [DateTime]::Now.ToString('o')
    target = 'FPSGAMEEditor Win64 Development'
    completed = $false
    runtime_tested = $false
}
function Get-BusyProcesses {
    # Waiting only: a cheap process-name snapshot avoids WMI allocation during
    # simultaneous skeletal-mesh imports. Never stop or modify these processes.
    @(Get-Process -Name UnrealEditor,UnrealEditor-Cmd,dotnet,UnrealBuildTool,cl,link -ErrorAction SilentlyContinue)
}
try {
    while (-not $held) {
        if ([DateTime]::UtcNow -gt $deadline) { throw 'The existing editor/build batch has not released the toolchain.' }
        try { $held = $gate.WaitOne(1000) }
        catch [Threading.AbandonedMutexException] { $held = $true }
        if (-not $held) {
            if ([DateTime]::UtcNow -ge $nextProgress) {
                Write-Output 'Waiting for the existing UE/native build batch; no duplicate build started.'
                $nextProgress = [DateTime]::UtcNow.AddSeconds(60)
            }
            Start-Sleep -Seconds 5
        }
    }
    while (@(Get-BusyProcesses).Count) {
        if ([DateTime]::UtcNow -gt $deadline) { throw 'The existing editor/build batch has not released the toolchain.' }
        if ([DateTime]::UtcNow -ge $nextProgress) {
            Write-Output 'UE batch gate held; waiting for the existing native process to exit.'
            $nextProgress = [DateTime]::UtcNow.AddSeconds(60)
        }
        Start-Sleep -Seconds 5
    }
    $receipt.build_started = [DateTime]::Now.ToString('o')
    Write-Output 'Starting the normal M870 hip-placement Editor build.'
    & (Join-Path $projectRoot 'Tools/Build/Build-Editor.ps1') *> (Join-Path $PSScriptRoot 'build_editor.log')
    if ($LASTEXITCODE -ne 0) { throw "Editor build returned $LASTEXITCODE." }
    $receipt.completed = $true
    $receipt.base_editor_dll_updated = $true
    Write-Output 'M870 hip-placement Editor build succeeded.'
} catch {
    $receipt.error = $_.Exception.Message
    throw
} finally {
    $receipt.finished = [DateTime]::Now.ToString('o')
    $receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
