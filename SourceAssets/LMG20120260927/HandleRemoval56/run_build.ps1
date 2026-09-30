$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
 $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))
 if(-not $taskHeld){throw 'Bridge batch busy; no build started'}
 $taskBuilders=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
 if($taskBuilders.Count){throw 'Existing native build retained; wait for its completion'}
 & "$taskRoot/Tools/Build/Build-Editor.ps1" *> "$PSScriptRoot/build_console.log"
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}