param([string]$Script='SourceAssets/BenelliM4Super9020261006/import_and_export.py',[string]$Log='SourceAssets/BenelliM4Super9020261006/import_assets_final.log')
$ErrorActionPreference='Stop'
$queueGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$queueHeld=$false
try {
    while(-not $queueHeld) {
        try {$queueHeld=$queueGate.WaitOne(30000)} catch [Threading.AbandonedMutexException] {$queueHeld=$true}
        if(-not $queueHeld){continue}
        $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','cl.exe','link.exe') })
        if($busy.Count -gt 0){$queueGate.ReleaseMutex();$queueHeld=$false;Start-Sleep -Seconds 15}
    }
    & 'D:/FPS3D/FPSGAME/Tools/ModularOutfit/Run-Authoring.ps1' -Script $Script -Log $Log
} finally {if($queueHeld){$queueGate.ReleaseMutex()};$queueGate.Dispose()}
