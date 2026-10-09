$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
 while(-not $taskHeld){
  try{$taskHeld=$taskGate.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
 }
 do {
  $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','cl.exe','link.exe')})
  if($busy.Count -gt 0){Start-Sleep -Seconds 5}
 } while($busy.Count -gt 0)
 & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1'
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
