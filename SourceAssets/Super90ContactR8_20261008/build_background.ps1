$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    for($attempt=0;$attempt -lt 60 -and -not $held;++$attempt) {
        try {$held=$gate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if($held) {
            $busy=@(Get-CimInstance Win32_Process | Where-Object {
                ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe')
            })
            if($busy.Count){$gate.ReleaseMutex();$held=$false;Start-Sleep -Seconds 15}
        }
    }
    if(-not $held){throw 'Existing editor/build remains active; no process was stopped.'}
    & "$root/Tools/Build/Build-Editor.ps1"
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
