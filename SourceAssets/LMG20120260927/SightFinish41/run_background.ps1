param([string]$taskScript='integrate.py',[string]$taskLog='production')
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
 $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))
 if(-not $taskHeld){throw 'Asset bridge busy; no production commandlet started'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing UE process retained; commandlet not started'}
 $taskBase='D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/SightFinish41'
 & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' '-run=pythonscript' "-script=$taskBase/$taskScript" '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$taskBase/$taskLog.log" *> "$taskBase/${taskLog}_console.log"
 exit $LASTEXITCODE
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
