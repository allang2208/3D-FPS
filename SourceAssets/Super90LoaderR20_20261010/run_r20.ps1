param()
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$importScript = Join-Path $PSScriptRoot 'import_r20.py'
$editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
    [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
})
if ($editors.Count) {
    $resultFile = Join-Path $PSScriptRoot ('import-bridge-' + [guid]::NewGuid().ToString('N') + '.txt')
    & "$projectRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $importScript -QueueWaitSeconds 60 -OutputFile $resultFile -MaxOutputChars 3000
    if (-not $?) { throw "Editor import did not finish; preserve this session and read $resultFile" }
    return
}

# Asset import only. No editor UI, native build, game launch, render or test.
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try {
        for ($attempt = 0; $attempt -lt 10 -and -not $held; $attempt++) {
            $held = $gate.WaitOne(60000)
            if (-not $held) { Write-Output 'Waiting for the existing UE asset batch gate; no asset write started.' }
        }
    }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous UE batch ended unexpectedly; no new asset write started.' }
    if (-not $held) { throw 'UE authoring gate is busy; no asset write started.' }
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and
            ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe')
    })
    if ($busy.Count) { throw 'An editor or native build became active; no commandlet started.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $log = Join-Path $PSScriptRoot "import-commandlet-$stamp.log"
    $console = Join-Path $PSScriptRoot "import-console-$stamp.log"
    $oldSkipSdk = $env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP = '1'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$importScript" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$log" *> $console
        if ($LASTEXITCODE -ne 0) { throw "Import failed; see $log" }
    } finally { $env:UE_SKIP_UBT_SDK_SETUP = $oldSkipSdk }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
