param([ValidateSet('install')][string]$Stage='install')
$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME';$m24Out=$PSScriptRoot
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m24Held=$false
try {
    try{$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m24Held=$true}
    if(-not $m24Held){throw 'Existing UE asset batch remains occupied.'}
    $m24Processes=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    $m24Deadline=[DateTime]::UtcNow.AddMinutes(15)
    while($m24Processes | Where-Object Name -eq 'UnrealEditor-Cmd.exe') {
        if([DateTime]::UtcNow -ge $m24Deadline){throw 'The existing commandlet is still busy; assets retained.'}
        Write-Output 'Waiting for the existing background asset process to exit.'
        $m24Busy=$m24Processes | Where-Object Name -eq 'UnrealEditor-Cmd.exe' | Select-Object -First 1
        try{[void][Diagnostics.Process]::GetProcessById($m24Busy.ProcessId).WaitForExit(45000)}catch [ArgumentException]{}
        $m24Processes=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    }
    $m24Stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    if($m24Processes | Where-Object Name -eq 'UnrealEditor.exe') {
        & "$m24Root/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$m24Out/$Stage.py" -QueueWaitSeconds 60 -RequestTimeoutSeconds 600 -OutputFile "$m24Out/$Stage-$m24Stamp.json" -MaxOutputChars 1200
    } else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$m24Root/FPSGAME.uproject" -run=pythonscript "-script=$m24Out/$Stage.py" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$m24Out/$Stage-$m24Stamp.log" *> "$m24Out/$Stage-$m24Stamp.stdout.txt"
    }
    if($LASTEXITCODE -ne 0){throw "M24 $Stage failed; see batch log."}
    Write-Output "M24 advanced action $Stage completed."
} finally {if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()}
