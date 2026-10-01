param([switch]$ImportOnly)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne(600000) } catch [Threading.AbandonedMutexException] { $held=$true }
    if(-not $held){throw 'HK416 ADS asset window is busy. No editor was started.'}
    if(-not $ImportOnly){
        & "$projectRoot/Tools/Build/Build-Editor.ps1"
    }
    & "$projectRoot/Tools/ModularOutfit/Run-Authoring.ps1" -Script SourceAssets/HK416ADS20260930/import_corrected_sights.py -Log SourceAssets/HK416ADS20260930/import_corrected_sights.log
} finally {
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
