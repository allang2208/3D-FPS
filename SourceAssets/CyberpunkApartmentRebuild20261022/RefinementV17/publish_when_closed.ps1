$ErrorActionPreference='Stop'
$taskDeadline=[DateTime]::UtcNow.AddMinutes(30)
$taskProjectPattern='(?i)D:[\/]FPS3D[\/]FPSGAME[\/]FPSGAME\.uproject(?:["\s]|$)'
while(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match $taskProjectPattern }) {
 if([DateTime]::UtcNow -ge $taskDeadline){throw 'Preserving the loaded editor; V17 production sources are ready, import pending.'}
 Start-Sleep -Seconds 8
}
& (Join-Path $PSScriptRoot 'publish_background.ps1') -RunName publish-01 -MaterialCompilation
