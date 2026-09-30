param([ValidateSet('materials','install')][string]$Phase='install')
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $taskHeld){throw 'Shared asset bridge busy; background save not started'}
    # Materials phase creates only new private F50 packages. It never saves an
    # existing mesh, source material or skeleton held by another UE process.
    if($Phase -eq 'install' -and (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue)){throw 'Existing UE process retained; current-asset save not started'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=pythonscript' "-script=$PSScriptRoot/$Phase.py" '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$PSScriptRoot/$Phase.log" *> "$PSScriptRoot/${Phase}_console.log"
    if($LASTEXITCODE -ne 0){throw "Background save failed: $LASTEXITCODE"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
