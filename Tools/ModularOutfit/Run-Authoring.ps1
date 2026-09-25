param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Log)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'Asset authoring window is busy; no commandlet was started.' }
    $editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if ($editors | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject' }) {
        throw 'An FPSGAME editor is running. Use the existing MCP bridge for this batch.'
    }
    $scriptPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $Script))
    $logPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $Log))
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$scriptPath" `
        -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen "-abslog=$logPath"
    if ($LASTEXITCODE -ne 0) { throw "Asset authoring failed ($LASTEXITCODE); see $logPath" }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
