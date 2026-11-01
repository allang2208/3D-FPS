param([string]$Stage = 'read_assets')
$ErrorActionPreference = 'Stop'
if ($Stage -notin @('read_assets','install','import_icons')) { throw 'Unknown M24 authoring stage.' }
$projectRoot = 'D:/FPS3D/FPSGAME'
$taskRoot = "$projectRoot/SourceAssets/M24SupportGrip20261027"
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    Write-Output 'Waiting for the existing UE asset batch mutex.'
    try { $held = $gate.WaitOne(600000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'UE asset batch remains occupied; the M24 import remains incomplete.' }
    $active = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject' })
    if ($active | Where-Object Name -eq 'UnrealEditor-Cmd.exe') {
        throw 'An active FPSGAME commandlet owns the project; source assets are retained.'
    }
    if ($active | Where-Object Name -eq 'UnrealEditor.exe') {
        $batchStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
        & "$projectRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$taskRoot/$Stage.py" -QueueWaitSeconds 60 -RequestTimeoutSeconds 600 -OutputFile "$taskRoot/${Stage}_bridge_$batchStamp.json" -MaxOutputChars 1800
        if ($LASTEXITCODE -ne 0) { throw 'The existing editor import batch did not complete.' }
    } else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
            "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/$Stage.py" `
            -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$taskRoot/$Stage.log"
        if ($LASTEXITCODE -ne 0) { throw 'M24 asset stage failed; see the stage log.' }
    }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
