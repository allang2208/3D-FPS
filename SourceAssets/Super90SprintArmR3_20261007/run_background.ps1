param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Log)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    for($attempt=0;$attempt -lt 20 -and -not $held;++$attempt) {
        try {$held=$gate.WaitOne(30000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if($held){
            $busy=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
            if($busy.Count){$gate.ReleaseMutex();$held=$false;Start-Sleep -Seconds 30}
        }
    }
    if(-not $held){throw 'UE authoring window remains busy; no process started.'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if($editors | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'}) {
        throw 'FPSGAME editor/commandlet is active. Preserve it and use the existing bridge when available.'
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$Script" `
        -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen "-abslog=$Log"
    if($LASTEXITCODE -ne 0){throw "Authoring failed ($LASTEXITCODE); see $Log"}
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
