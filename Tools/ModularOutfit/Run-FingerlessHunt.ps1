param([string]$Script='Tools/ModularOutfit/import_fingerless_hunt_v2.py',[string]$Batch='import-final')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    for($attempt=0;$attempt -lt 5 -and -not $held;$attempt++) {
        try {$held=$gate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if(-not $held){Write-Output 'Waiting for the current asset batch to release the existing UE bridge mutex.'}
    }
    if(-not $held){throw 'Asset authoring window is busy; no commandlet was started.'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if($editors | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'}) {
        throw 'FPSGAME is running. Preserve it and use the existing editor bridge, or resume background import after it closes.'
    }
    $scriptPath=Join-Path $projectRoot $Script
    $logPath=Join-Path $projectRoot "SourceAssets/ModularOutfit20260926/FingerlessHuntV2/$Batch.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -nosound `
        -AllowCommandletRendering -RenderOffscreen -ModelContextProtocolPort=18049 `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$logPath"
    if($LASTEXITCODE -ne 0){throw "Fingerless glove authoring failed ($LASTEXITCODE); see $logPath"}
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
