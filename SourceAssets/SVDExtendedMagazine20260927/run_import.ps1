param([int]$QueueSeconds=60)
$ErrorActionPreference='Stop'
$taskDir='D:/FPS3D/FPSGAME/SourceAssets/SVDExtendedMagazine20260927'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$bridge=$false
try {
    try {
        $until=(Get-Date).AddSeconds($QueueSeconds)
        do {$held=$gate.WaitOne([TimeSpan]::FromSeconds([Math]::Min(50,$QueueSeconds)))} while(-not $held -and (Get-Date) -lt $until)
    }
    catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch ended unexpectedly; preserve state.'}
    if(-not $held){throw 'UE batch gate occupied; no import started.'}
    $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" | Where-Object {
        $_.Name -in @('cl.exe','link.exe') -or -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME|UnrealBuildTool'
    })
    if($running | Where-Object {$_.Name -ne 'UnrealEditor.exe'}){throw 'Existing build or commandlet active; import has not started.'}
    if($running.Count){$bridge=$true}
    else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskDir/import_assets.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$taskDir/import_assets.log" *> "$taskDir/import_assets.stdout.log"
        $result=$LASTEXITCODE
        Select-String -LiteralPath "$taskDir/import_assets.log" -Pattern 'LogPython:.*(SVD_EXTMAG|Error|Traceback)' | Select-Object -Last 12 | ForEach-Object {$_.Line}
        if($result -ne 0){throw "SVD asset import failed: $result"}
    }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
if($bridge){
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript "$taskDir/import_assets.py" -QueueWaitSeconds 60 -OutputFile "$taskDir/import_assets.$stamp.bridge.json" -MaxOutputChars 3000
    if($LASTEXITCODE -ne 0){throw 'Existing-editor import did not complete.'}
}
