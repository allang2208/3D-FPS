param([int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$exteriorGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$exteriorHeld=$false
try {
    $exteriorHeld=$exteriorGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
    if(-not $exteriorHeld){throw 'UE production window busy; no native build started.'}
    & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' *> "$PSScriptRoot/native-build.log"
    Write-Output 'Exterior authoring module build complete.'
} finally {
    if($exteriorHeld){$exteriorGate.ReleaseMutex()}
    $exteriorGate.Dispose()
}
