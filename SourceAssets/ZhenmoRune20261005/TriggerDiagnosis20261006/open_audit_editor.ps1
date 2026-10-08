$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(10))} catch [Threading.AbandonedMutexException] {$held=$true}
 if (-not $held) {throw 'UE bridge busy'}
 if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {throw 'Existing editor preserved; use its bridge'}
 $args=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','/Game/GameMaps/DayNight_Lighting','-ColdSteelProfile=ZhenmoVisualAudit20261006','-ZhenmoVisualAudit','-ZhenmoAuditLabel=baseline','-ClearwaterNoMenu','-nosplash','-nop4','-abslog=D:/FPS3D/FPSGAME/SourceAssets/ZhenmoRune20261005/TriggerDiagnosis20261006/editor-audit.log')
 $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -PassThru
 Write-Output ('ZHENMO_EDITOR_PID '+$p.Id)
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}