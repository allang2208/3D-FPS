param([ValidateSet('read_inputs','read_stock_contact')][string]$Stage='read_inputs')
$ErrorActionPreference='Stop'
$stockRoot='D:/FPS3D/FPSGAME'
$stockOut=$PSScriptRoot
$stockGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$stockHeld=$false
try {
    try {$stockHeld=$stockGate.WaitOne([TimeSpan]::FromMinutes(15))} catch [Threading.AbandonedMutexException] {$stockHeld=$true}
    if(-not $stockHeld){throw 'Existing UE asset batch remains occupied.'}
    $stockProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    $stockDeadline=[DateTime]::UtcNow.AddMinutes(15)
    while($stockProcesses | Where-Object Name -eq 'UnrealEditor-Cmd.exe') {
        if([DateTime]::UtcNow -ge $stockDeadline){throw 'Existing commandlet is still busy; assets retained.'}
        $stockBusy=$stockProcesses | Where-Object Name -eq 'UnrealEditor-Cmd.exe' | Select-Object -First 1
        try {[void][Diagnostics.Process]::GetProcessById($stockBusy.ProcessId).WaitForExit(45000)} catch [ArgumentException] {}
        $stockProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    }
    $stockStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    if($stockProcesses | Where-Object Name -eq 'UnrealEditor.exe') {
        & "$stockRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$stockOut/$Stage.py" -QueueWaitSeconds 60 -RequestTimeoutSeconds 600 -OutputFile "$stockOut/$Stage-$stockStamp.json" -MaxOutputChars 1200
    } else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$stockRoot/FPSGAME.uproject" -run=pythonscript "-script=$stockOut/$Stage.py" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$stockOut/$Stage-$stockStamp.log" *> "$stockOut/$Stage-$stockStamp.stdout.txt"
    }
    if($LASTEXITCODE -ne 0){throw "Stock $Stage failed; see batch log."}
    Write-Output "Skeleton sniper stock $Stage completed."
} finally {
    if($stockHeld){$stockGate.ReleaseMutex()}
    $stockGate.Dispose()
}
