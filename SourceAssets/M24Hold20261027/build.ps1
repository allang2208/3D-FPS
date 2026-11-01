$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$taskRoot = "$projectRoot/SourceAssets/M24Hold20261027"
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(600000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'UE asset batch remains occupied.' }
    $active = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject' })
    if ($active.Count) { throw 'FPSGAME is already open. Retaining the existing process and its assets.' }
    & "$projectRoot/Tools/Build/Build-Editor.ps1"
    if ($LASTEXITCODE -ne 0) { throw 'M24 build failed.' }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
