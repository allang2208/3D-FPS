param([int]$MaximumEditorWaitSeconds=1800)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskFolder=Join-Path $taskRoot 'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV9'
$taskPattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumEditorWaitSeconds)
while(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match $taskPattern}) {
 if([DateTime]::UtcNow -gt $taskDeadline){throw 'Editor retained. Searchlight sources remain ready; no external asset overwrite attempted.'}
 Start-Sleep -Seconds 8
}
& (Join-Path $taskFolder 'publish_background.ps1') -RunName 'publish-03'
