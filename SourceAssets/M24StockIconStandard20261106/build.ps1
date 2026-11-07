param()
$ErrorActionPreference='Stop'
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$m24Held=$false
try {
 try {$m24Held=$m24Gate.WaitOne(1800000)} catch [Threading.AbandonedMutexException] {$m24Held=$true}
 if(-not $m24Held){throw 'Asset bridge remained busy; build not dispatched.'}
 $m24Deadline=(Get-Date).AddMinutes(15)
 do {
  $m24Active=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
  if($m24Active | Where-Object Name -eq 'UnrealEditor.exe'){throw 'Interactive editor active; build retained without stopping it.'}
  if(-not $m24Active){break}
  if((Get-Date) -gt $m24Deadline){throw 'Existing commandlet retained; build deferred.'}
  Start-Sleep -Seconds 4
 } while ($true)
 & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' *> "$PSScriptRoot/build.log"
 if($LASTEXITCODE -ne 0){throw "Editor build failed: $LASTEXITCODE"}
 Write-Output 'M24 source compiled into the ordinary editor DLL. No editor or gameplay started.'
} finally {if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()}
