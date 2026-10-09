$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
# Wait on the same production batch mutex; never contact another task or start
# a competing editor. Run-Authoring performs its normal editor/process guard.
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne(600000) } catch [Threading.AbandonedMutexException] { $held=$true }
    if(-not $held){throw 'Asset production batch is still occupied; authoring files remain saved.'}
    & "$projectRoot/Tools/ModularOutfit/Run-Authoring.ps1" -Script 'SourceAssets/Super90Foregrips20261007/import_assets.py' -Log 'SourceAssets/Super90Foregrips20261007/import_assets.log'
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
