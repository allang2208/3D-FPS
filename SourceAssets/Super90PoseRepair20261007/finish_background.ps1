$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$out="$root/SourceAssets/Super90PoseRepair20261007"
function Record-Stage([string]$Stage) {
    [IO.File]::AppendAllText("$out/production_status.log", [DateTime]::UtcNow.ToString('o')+' '+$Stage+[Environment]::NewLine)
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    Record-Stage 'Waiting for the existing authoring batch.'
    while(-not $held) {
        try {$held=$gate.WaitOne(30000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
    Record-Stage 'Batch lock acquired; waiting for loaded editors and compilers to finish.'
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','cl.exe','link.exe')})
        if($busy.Count -gt 0){Start-Sleep -Seconds 5}
    } while($busy.Count -gt 0)
    Record-Stage 'Building FPSGAMEEditor.'
    & "$root/Tools/Build/Build-Editor.ps1" *> "$out/build_editor.log"
    Record-Stage 'Editor target build succeeded. Importing the repaired animation assets.'
    & "$root/Tools/ModularOutfit/Run-Authoring.ps1" `
        -Script 'SourceAssets/Super90PoseRepair20261007/import_animations.py' `
        -Log 'SourceAssets/Super90PoseRepair20261007/import_commandlet.log' `
        *> "$out/import_commandlet_console.log"
    Record-Stage 'Animation import and saving completed. Runtime and visual testing not performed.'
} finally {
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
