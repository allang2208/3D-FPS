param([switch]$ImportOnly)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne(600000) } catch [Threading.AbandonedMutexException] { $held=$true }
    if(-not $held){throw 'HK416 production window remained busy. No editor was started.'}
    if(-not $ImportOnly){
        & "$projectRoot/Tools/Build/Build-Editor.ps1"
        if($LASTEXITCODE -ne 0){throw 'HK416 native build did not complete.'}
    }
    & "$projectRoot/Tools/ModularOutfit/Run-Authoring.ps1" -Script SourceAssets/HK416Reworked20260930/import_all.py -Log SourceAssets/HK416Reworked20260930/import_all.log
} finally {
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
