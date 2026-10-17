param([string]$Script='export_donor.py',[string]$Log='export_donor.log')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/M870Tactical20261015'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(600000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    & 'D:/FPS3D/FPSGAME/Tools/ModularOutfit/Run-Authoring.ps1' -Script "SourceAssets/M870Tactical20261015/$Script" -Log "SourceAssets/M870Tactical20261015/$Log"
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
