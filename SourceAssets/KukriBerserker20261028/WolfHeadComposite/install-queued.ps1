param([string]$PythonName='install_head.py',[switch]$CompileShaders)
$ErrorActionPreference='Stop'
$runeProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$runeDeadline=(Get-Date).AddMinutes(20)
while ((Get-Date) -lt $runeDeadline) {
    $runeProcesses=@(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($runeProject) })
    if (@($runeProcesses | Where-Object Name -eq 'UnrealEditor.exe').Count) {
        $runeOutput=Join-Path $PSScriptRoot ('install-bridge-'+[Guid]::NewGuid().ToString('N')+'.txt')
        & 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1' -PythonScript (Join-Path $PSScriptRoot $PythonName) -OutputFile $runeOutput -MaxOutputChars 2200 -QueueWaitSeconds 60 -RequestTimeoutSeconds 180
        exit $LASTEXITCODE
    }
    if ($runeProcesses.Count) {
        Write-Output 'Waiting for the current background asset process to finish.'
        Wait-Process -Id $runeProcesses.ProcessId -Timeout 45 -ErrorAction SilentlyContinue
        continue
    }
    $runeGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $runeHeld=$false
    try {
        try {$runeHeld=$runeGate.WaitOne([TimeSpan]::FromSeconds(45))}
        catch [Threading.AbandonedMutexException] {$runeHeld=$true;throw 'Previous asset batch ended unexpectedly; preserve its state.'}
        if (-not $runeHeld) {continue}
        # The same gate covers the complete import/save batch.
        & (Join-Path $PSScriptRoot 'run-background.ps1') -PythonName $PythonName -CompileShaders:$CompileShaders
        exit $LASTEXITCODE
    } finally {
        if ($runeHeld) {$runeGate.ReleaseMutex()}
        $runeGate.Dispose()
    }
}
throw 'Asset import remains queued; the editable model, textures and material sources are saved.'
