$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
function Get-TaskEditor {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
}
function Invoke-TaskBridge {
    & "$taskRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript (Join-Path $PSScriptRoot 'import_assets.py') -QueueWaitSeconds 60 -RequestTimeoutSeconds 600 -MaxOutputChars 2500 -OutputFile (Join-Path $PSScriptRoot ('import-bridge-'+[guid]::NewGuid().ToString('N')+'.json'))
    if ($LASTEXITCODE -ne 0) { throw "Seat bridge import failed: $LASTEXITCODE" }
}
if ((Get-TaskEditor).Count -gt 0) {
    Invoke-TaskBridge
} else {
    $taskGate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $taskHeld = $false
    $taskUseBridge = $false
    try {
        for ($taskAttempt=0; $taskAttempt -lt 20 -and -not $taskHeld; $taskAttempt++) {
            try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        }
        if (-not $taskHeld) {throw 'Asset batch remains busy; no import started.'}
        while (@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll')}).Count -gt 0) {
            Start-Sleep -Seconds 5
        }
        if ((Get-TaskEditor).Count -gt 0) {
            $taskUseBridge = $true
        } else {
            $env:UE_SKIP_UBT_SDK_SETUP='1'
            & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript ('-script='+$PSScriptRoot+'\import_assets.py') -unattended -nop4 -nosplash -NoSound -NoLiveCoding -AllowCommandletRendering -RenderOffscreen -d3d12 -sm6 -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'\import-engine.log') *> (Join-Path $PSScriptRoot 'import-console.log')
            if ($LASTEXITCODE -ne 0) {throw "Seat import commandlet failed: $LASTEXITCODE"}
        }
    } finally {
        if ($taskHeld) {$taskGate.ReleaseMutex()}
        $taskGate.Dispose()
    }
    if ($taskUseBridge) {Invoke-TaskBridge}
}
