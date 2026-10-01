param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Log)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'The UE authoring batch is busy.' }
    $running = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if ($running | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject' }) { throw 'This project is open; use its existing serialized bridge. No editor was stopped.' }
    $compilers = @(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'")
    if ($compilers | Where-Object { $_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool' }) { throw 'An existing compiler is running; no commandlet was submitted.' }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$projectRoot/$Script" -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen "-abslog=$projectRoot/$Log"
    if ($LASTEXITCODE -ne 0) { throw "HK416 asset authoring failed ($LASTEXITCODE); see $Log" }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
