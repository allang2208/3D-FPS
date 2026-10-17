$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskScript=Join-Path $taskProject 'Tools\Skills\import_ice_armor_v6.py'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskOwns=$false
$taskUseBridge=$false
try {
    while(-not $taskOwns){try{$taskOwns=$taskGate.WaitOne(60000)}catch [Threading.AbandonedMutexException]{$taskOwns=$true}}
    # These are new, task-owned packages. Other commandlets with different
    # output packages and Game-only builds do not write the assets or DLLs used here.
    while($taskActive=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'import_ice_armor_v6|ThirdPersonV6') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat.*FPSGAMEEditor')})) {
        foreach($taskProcess in $taskActive){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
    }
    $taskUseBridge=[bool](Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME'})
    if(-not $taskUseBridge){
        & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosplash -nosound -RenderOffscreen -AllowCommandletRendering "-abslog=$PSScriptRoot\import.log" *> "$PSScriptRoot\import-console.txt"
        $taskCode=$LASTEXITCODE
        Get-Content -LiteralPath "$PSScriptRoot\import-console.txt" -Tail 16
        if($taskCode -ne 0){exit $taskCode}
    }
} finally {if($taskOwns){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
if($taskUseBridge){
    $taskBridgeLog=Join-Path $PSScriptRoot ('import-bridge-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.txt')
    & "$taskProject\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript $taskScript -OutputFile $taskBridgeLog -QueueWaitSeconds 900 -RequestTimeoutSeconds 3600
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
}
