$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
 $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))
 if(-not $taskHeld){throw 'Shared bridge busy; no capture started'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing editor retained'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=pythonscript' "-script=$PSScriptRoot/install.py" '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$PSScriptRoot/install.log" *> "$PSScriptRoot/install_console.log"
 if($LASTEXITCODE -ne 0){throw "HandleRemoval56 asset publication failed $LASTEXITCODE"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
