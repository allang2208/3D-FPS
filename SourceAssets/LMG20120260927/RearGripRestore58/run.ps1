param([string]$Script='collect',[int]$QueueWaitSeconds=60)
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
 $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
 if(-not $taskHeld){throw 'Shared bridge busy; no commandlet started'}
 $taskEditors=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and ($_.CommandLine -replace '\\','/') -match '(?i)D:/FPS3D/FPSGAME/FPSGAME.uproject' }
 if($taskEditors){throw 'Existing FPSGAME editor retained; use bridge instead'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=pythonscript' "-script=$PSScriptRoot/$Script.py" '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$PSScriptRoot/$Script.log" *> "$PSScriptRoot/${Script}_console.log"
 if($LASTEXITCODE -ne 0){throw "RearGripRestore58 commandlet failed $LASTEXITCODE"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
