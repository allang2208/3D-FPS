param([ValidateSet('read_assets','install')][string]$Stage='read_assets')
$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME'
$m24Out="$m24Root/SourceAssets/M24SprintSupport20261028"
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m24Held=$false
try {
    try{$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m24Held=$true}
    if(-not $m24Held){throw 'Existing UE batch remains occupied.'}
    $m24Processes=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape("$m24Root/FPSGAME.uproject") -or $_.CommandLine -match [regex]::Escape('D:\FPS3D\FPSGAME\FPSGAME.uproject')})
    if($m24Processes | Where-Object Name -eq 'UnrealEditor-Cmd.exe'){throw 'A commandlet owns the project; assets retained.'}
    $m24Stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    if($m24Processes | Where-Object Name -eq 'UnrealEditor.exe') {
        & "$m24Root/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$m24Out/$Stage.py" -QueueWaitSeconds 60 -RequestTimeoutSeconds 600 -OutputFile "$m24Out/$Stage-$m24Stamp.json" -MaxOutputChars 2000
    } else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$m24Root/FPSGAME.uproject" -run=pythonscript "-script=$m24Out/$Stage.py" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$m24Out/$Stage-$m24Stamp.log" *> "$m24Out/$Stage-$m24Stamp.stdout.txt"
    }
    if($LASTEXITCODE -ne 0){throw "M24 $Stage failed; see this batch log."}
    Write-Output "M24 $Stage completed."
} finally {if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()}
