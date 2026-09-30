$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $taskHeld){throw 'Asset bridge busy; commandlet not started'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing UE process retained; commandlet not started'}
    $taskBase=$PSScriptRoot
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' '-run=pythonscript' "-script=$taskBase/install.py" '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$taskBase/import.log" *> "$taskBase/import_console.log"
    exit $LASTEXITCODE
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
