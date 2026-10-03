param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Log)
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while ($true) {
        try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if (-not $taskHeld) {continue}
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
        if ($taskEditors | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {throw 'FPSGAME editor is open; use its existing bridge. No editor was stopped.'}
        $taskBuilders=@(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if ($taskEditors.Count -eq 0 -and $taskBuilders.Count -eq 0) {break}
        $taskGate.ReleaseMutex();$taskHeld=$false
        Start-Sleep -Seconds 15
    }
    & 'D:\FPS3D\FPSGAME\Tools\ModularOutfit\Run-Authoring.ps1' -Script $Script -Log $Log
    if ($LASTEXITCODE -ne 0) {throw 'RSH-12 authoring did not complete.'}
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}