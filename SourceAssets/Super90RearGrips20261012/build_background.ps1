$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(300))
    if(-not $held){throw 'UE batch gate remains occupied; no process was stopped.'}
    & "$projectRoot/Tools/Build/Build-Editor.ps1"
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
