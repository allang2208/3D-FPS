param([ValidateSet('Import','Render','Finalize')][string]$Mode='Import')
$ErrorActionPreference='Stop'
$caseDir='D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/UVRepair'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(900))} catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.' }
 if(-not $held){throw 'UE batch gate unavailable; no changes made.'}
 $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME' })
 if($editors.Count){throw 'FPSGAME is running. Use the existing bridge; no second asset writer started.'}
 $taskArgs=if($Mode -eq 'Import'){@('-run=pythonscript',"-script=$caseDir/import_all.py",'-nullrhi')}elseif($Mode -eq 'Finalize'){@('-run=pythonscript',"-script=$caseDir/finalize.py",'-nullrhi')}else{@('-run=ColdSteelWeaponIconCatalog','-Definition=ue_svd','-AllowCommandletRendering','-RenderOffscreen','-NoSound','-NoTextureStreaming')}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' @taskArgs -unattended -nop4 -nosplash "-abslog=$caseDir/ue_${Mode}_final.log" *> "$caseDir/stdout_${Mode}_final.log"
 $code=$LASTEXITCODE
 Select-String -Path "$caseDir/ue_${Mode}_final.log" -Pattern 'SVD_UV_|WeaponIconCatalog: COMPLETE|Traceback|Error:' | Select-Object -Last 14 | ForEach-Object {$_.Line}
 exit $code
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
