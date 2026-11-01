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
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=M24HoldReview -AllowCommandletRendering `
        -NoTextureStreaming -unattended -nosplash -nosound -RenderOffscreen  `
        "-Output=$taskRoot/UEReview" "-abslog=$taskRoot/hold_render.log"
    if ($LASTEXITCODE -ne 0) { throw 'M24 catalog render failed; see hold_render.log.' }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
