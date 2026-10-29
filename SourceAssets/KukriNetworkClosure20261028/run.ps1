param([ValidateSet('Editor','Game','Audit','Assets')][string]$Stage='Editor')
$ErrorActionPreference='Stop'
$taskRoot='D:\FPS3D\FPSGAME\SourceAssets\KukriNetworkClosure20261028'
$taskProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskBuilds=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool' })
foreach($taskExisting in $taskBuilds) {
    $taskProcess=Get-Process -Id $taskExisting.ProcessId -ErrorAction SilentlyContinue
    if($taskProcess) { Write-Output "Waiting for the existing build process $($taskExisting.ProcessId)."; $taskProcess.WaitForExit() }
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))
    if(-not $taskHeld) {throw 'Shared UE batch is occupied; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue) {throw 'An editor/game is active; leaving it unchanged.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool'}) {throw 'Another build started; nothing started.'}
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog=Join-Path $taskRoot "$Stage-$taskStamp.log"
    $taskConsole=Join-Path $taskRoot "$Stage-$taskStamp-console.log"
    if($Stage -in @('Editor','Game')) {
        $taskTarget=if($Stage -eq 'Editor'){'FPSGAMEEditor'}else{'FPSGAME'}
        & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $taskTarget Win64 Development "-Project=$taskProject" -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog" *> $taskConsole
    } else {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $taskRun=if($Stage -eq 'Audit'){@('-run=KukriNetworkAudit',"-Output=$taskRoot\authority-checks.json")}else{@('-run=pythonscript',"-script=$taskRoot\read_assets.py")}
        & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $taskProject @taskRun -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile -AssetGatherAll=false '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$taskLog" -stdout -FullStdOutLogOutput *> $taskConsole
    }
    $taskExit=$LASTEXITCODE
    [ordered]@{stage=$Stage;exit_code=$taskExit;completed=(Get-Date -Format o);log=$taskLog;console=$taskConsole;udp_tested=$false;visuals_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot "$Stage-result.json") -Encoding utf8
    Get-Content -LiteralPath $taskConsole -Tail 18
    exit $taskExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskOldSdk
    if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()
}