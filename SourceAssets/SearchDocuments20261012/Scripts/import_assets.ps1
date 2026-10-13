$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskScript=Join-Path $PSScriptRoot 'import_assets.py'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while ($true) {
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        foreach($taskEntry in $taskBusy){
            $taskProcess=Get-Process -Id $taskEntry.ProcessId -ErrorAction SilentlyContinue
            if($taskProcess){Write-Output ('Waiting for active UE operation '+$taskEntry.ProcessId);$taskProcess.WaitForExit()}
        }
        try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if(-not $taskHeld){throw 'UE asset batch lock unavailable; source assets preserved'}
        if(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue){
            $taskMutex.ReleaseMutex();$taskHeld=$false
            & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript -QueueWaitSeconds 60 -RequestTimeoutSeconds 600 -OutputFile (Join-Path $taskRoot ('Receipts/bridge-import-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.txt')) -MaxOutputChars 2200
            exit $LASTEXITCODE
        }
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if($taskBusy.Count -eq 0){break}
        $taskMutex.ReleaseMutex();$taskHeld=$false
    }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskRoot\Receipts\ue-import.log" *> (Join-Path $taskRoot 'Receipts/import-stdout.log')
    $taskExit=$LASTEXITCODE
    Write-Output "DOCUMENT_ASSET_IMPORT_EXIT=$taskExit"
    Select-String -LiteralPath (Join-Path $taskRoot 'Receipts/import-stdout.log') -Pattern 'SEARCH_DOCUMENT|Error:|Traceback' | Select-Object -Last 18
    exit $taskExit
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
