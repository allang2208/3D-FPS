param([string]$OutputName='Compare',[string]$Manifest='surface_manifest.json')
$ErrorActionPreference='Stop'
$finishGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$finishHeld=$false
try {
 try{$finishHeld=$finishGate.WaitOne(60000)}catch [Threading.AbandonedMutexException]{$finishHeld=$true}
 if(-not $finishHeld){throw 'Bridge occupied; no render dispatched.'}
 if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'}){throw 'Shared editor or commandlet preserved.'}
 $finishOutput=Join-Path $PSScriptRoot $OutputName
 [IO.Directory]::CreateDirectory($finishOutput) | Out-Null
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=M24HoldReview "-SurfaceManifest=$PSScriptRoot/$Manifest" "-Output=$finishOutput" -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen -d3d12 '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$finishOutput/capture.log" *> "$finishOutput/capture-console.log"
 if($LASTEXITCODE -ne 0){throw "M24 material comparison failed: $LASTEXITCODE"}
 Write-Output 'M24 material comparison saved.'
}finally{if($finishHeld){$finishGate.ReleaseMutex()};$finishGate.Dispose()}
