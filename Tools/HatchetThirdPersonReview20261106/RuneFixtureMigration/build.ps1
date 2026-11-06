$ErrorActionPreference='Stop'
$buildGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$buildHeld=$false
try {
    try{$buildHeld=$buildGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$buildHeld=$true;throw 'Interrupted prior UE batch preserved.'}
    if(-not $buildHeld){throw 'UE batch occupied.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE -MaxParallelActions=4 *> "$PSScriptRoot/build-latest.log"
    if($LASTEXITCODE -ne 0){throw "Build failed: $LASTEXITCODE"}
    Write-Output 'HATCHET_BUILD_OK'
} finally {if($buildHeld){$buildGate.ReleaseMutex()};$buildGate.Dispose()}
