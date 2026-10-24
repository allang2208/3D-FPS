param([int]$MaximumEditorWaitSeconds=1800)
$ErrorActionPreference='Stop'
$taskFolder='D:/FPS3D/FPSGAME/SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV11'
$taskPattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumEditorWaitSeconds)
while(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match $taskPattern}){
 if([DateTime]::UtcNow -gt $taskDeadline){throw 'Editor retained; tower sources saved without overwriting loaded assets.'}
 Start-Sleep -Seconds 8
}
& (Join-Path $taskFolder 'publish_background.ps1') -RunName 'publish-01' -MaterialCompilation
