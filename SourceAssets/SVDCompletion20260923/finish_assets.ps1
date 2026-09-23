$ErrorActionPreference='Stop'
$caseDir='D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try { $held=$gate.WaitOne([TimeSpan]::FromSeconds(900)) } catch [Threading.AbandonedMutexException] { $held=$true }
 if(-not $held){throw 'UE batch gate unavailable; no changes made.'}
 $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME' })
 if($editors.Count){throw 'FPSGAME editor is running. Use the existing project bridge for finish_assets.py.'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$caseDir/finish_assets.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$caseDir/finish_assets.log" *> "$caseDir/finish_assets_stdout.log"
 $code=$LASTEXITCODE
 Get-Content "$caseDir/finish_assets.log" -Tail 20
 exit $code
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
