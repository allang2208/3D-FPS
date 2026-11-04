param([string]$ScriptName = 'import_agile_grip.py', [int]$QueueWaitSeconds = 600)
$ErrorActionPreference = 'Stop'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] {
        $held = $true
        throw 'Prior UE operation has unknown completion; no import was launched.'
    }
    if (-not $held) { throw 'UE batch gate is busy; no import was launched.' }
    $builders = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')) -and
        $_.CommandLine -match '\bFPSGAMEEditor\b'
    })
    if ($builders.Count -gt 0) { throw 'An Editor native build is active; preserve it and wait.' }
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    $logName = [IO.Path]::GetFileNameWithoutExtension($ScriptName)
    # This batch owns only newly named agile-grip packages. It does not load/save
    # a map or replace the assets used by the existing editor process.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -NullRHI -nosound "-abslog=$PSScriptRoot/$logName.log" *> "$PSScriptRoot/$logName-console.log"
    $code=$LASTEXITCODE
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
exit $code
