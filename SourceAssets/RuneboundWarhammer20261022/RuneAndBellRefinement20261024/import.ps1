$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskEngine='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    Write-Output 'Waiting for shared asset batch gate'
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){Write-Output 'Asset batch gate busy; no engine request sent';exit 75}
    Write-Output 'Asset batch gate acquired'
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {throw 'Preserving running editor; use the existing bridge for this import.'}
    # Existing commandlets finish before this package write batch starts.
    foreach($taskProcess in @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'")) {
        Write-Output ('Waiting for existing commandlet process '+$taskProcess.ProcessId)
        try {Wait-Process -Id $taskProcess.ProcessId -ErrorAction Stop} catch [Microsoft.PowerShell.Commands.ProcessCommandException] {}
    }
    Write-Output 'Starting background asset import'
    & $taskEngine $taskProject -run=pythonscript ('-script='+$taskRoot+'\install_assets.py') -unattended -nop4 -nosplash -NoSound -NoLiveCoding -RenderOffscreen -stdout -FullStdOutLogOutput ('-abslog='+$taskRoot+'\import-engine.log') *> ($taskRoot+'\import-console.log')
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;finished=(Get-Date).ToString('s');mode='Background commandlet under shared asset batch mutex';tests_run=$false} | ConvertTo-Json | Set-Content -LiteralPath ($taskRoot+'\import-process.json') -Encoding utf8
    if($taskExit -ne 0) {Get-Content -LiteralPath ($taskRoot+'\import-console.log') -Tail 35;exit $taskExit}
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
