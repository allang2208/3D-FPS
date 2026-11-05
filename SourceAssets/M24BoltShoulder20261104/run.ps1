param([Parameter(Mandatory=$true)][string]$Script)
$ErrorActionPreference='Stop'
$finishRoot='D:/FPS3D/FPSGAME'
$finishGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$finishHeld=$false
try {
 try{$finishHeld=$finishGate.WaitOne(300000)}catch [Threading.AbandonedMutexException]{$finishHeld=$true}
 if(-not $finishHeld){throw 'Asset bridge busy; no work dispatched.'}
 $finishActive=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
 if($finishActive | Where-Object Name -eq 'UnrealEditor-Cmd.exe'){throw 'Existing project commandlet preserved.'}
 $finishPath=Join-Path $PSScriptRoot $Script
 $finishStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
 if($finishActive | Where-Object Name -eq 'UnrealEditor.exe'){
  & "$finishRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $finishPath -OutputFile "$PSScriptRoot/$Script-$finishStamp.txt" -MaxOutputChars 2500 -RequestTimeoutSeconds 900
 }else{
  $env:UE_SKIP_UBT_SDK_SETUP='1'
  & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$finishRoot/FPSGAME.uproject" -run=pythonscript "-script=$finishPath" -unattended -nop4 -nosplash -nosound -nullrhi -NoLiveCoding '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$PSScriptRoot/$Script-$finishStamp.log" *> "$PSScriptRoot/$Script-$finishStamp-console.log"
 }
 if($LASTEXITCODE -ne 0){throw "M24 asset operation failed: $LASTEXITCODE"}
 Write-Output "Completed $Script"
}finally{if($finishHeld){$finishGate.ReleaseMutex()};$finishGate.Dispose()}
