param([string]$Script='D:/FPS3D/FPSGAME/Tools/BackpackMotion/save_refit_r2.py',[string]$ReceiptName='refit')
# Isolated asset authoring host: reads existing content; the script saves only a
# new MountainR2 package, so an open primary editor's loaded assets stay intact.
$ErrorActionPreference='Stop'
$packProject='D:/FPS3D/FPSGAME'
$packHost=Join-Path $packProject 'Saved/BackpackMotionAuthoring'
[IO.Directory]::CreateDirectory($packHost)|Out-Null
$packContent=Join-Path $packHost 'Content'
if(-not (Test-Path -LiteralPath $packContent)){New-Item -ItemType Junction -Path $packContent -Target (Join-Path $packProject 'Content')|Out-Null}
$packDescriptor=Join-Path $packHost 'BackpackMotionAuthoring.uproject'
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},@{Name='GeometryScripting';Enabled=$true})}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $packDescriptor -Encoding utf8
$packGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$packHeld=$false
try {
    try {$packHeld=$packGate.WaitOne()} catch [Threading.AbandonedMutexException] {$packHeld=$true}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $packDescriptor -run=pythonscript "-script=$Script" -unattended -nop4 -nosplash -AllowCommandletRendering -RenderOffscreen "-abslog=$packHost/$ReceiptName.log" *> (Join-Path $packHost ($ReceiptName+'.stdout.log'))
    $packExit=$LASTEXITCODE
    Get-Content -LiteralPath (Join-Path $packHost ($ReceiptName+'.log')) -Tail 10
    exit $packExit
} finally {if($packHeld){$packGate.ReleaseMutex()};$packGate.Dispose()}
