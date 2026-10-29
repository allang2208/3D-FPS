$ErrorActionPreference='Stop'
$dualRoot='D:\FPS3D\FPSGAME'
$dualOut=Join-Path $dualRoot 'SourceAssets\KukriDualCombatThirdPerson20261028'
$dualProject=Join-Path $dualRoot 'FPSGAME.uproject'
$dualGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$dualHeld=$false
$dualSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $dualHeld=$dualGate.WaitOne([TimeSpan]::FromSeconds(600))
    if(-not $dualHeld){throw 'UE batch is occupied; no build or asset write started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'An editor/game is active; leaving its assets unchanged.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Another build is active; nothing started.'}
    foreach($dualTarget in @('FPSGAMEEditor','FPSGAME')) {
        $dualLog=Join-Path $dualOut ($dualTarget+'-build.log')
        $dualConsole=Join-Path $dualOut ($dualTarget+'-build-console.log')
        & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $dualTarget Win64 Development "-Project=$dualProject" -NoHotReload -NoHotReloadFromIDE "-Log=$dualLog" *> $dualConsole
        $dualExit=$LASTEXITCODE
        @{target=$dualTarget;exit_code=$dualExit;completed=(Get-Date -Format o);runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dualOut ($dualTarget+'-build-result.json')) -Encoding utf8
        Get-Content -LiteralPath $dualConsole -Tail 12
        if($dualExit -ne 0 -and $dualTarget -eq 'FPSGAMEEditor'){exit $dualExit}
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $dualProject '-run=pythonscript' ('-script='+(Join-Path $dualOut 'save_all.py')) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile -NoLiveCoding -AssetGatherAll=false `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $dualOut 'save-engine.log')) -stdout -FullStdOutLogOutput *> (Join-Path $dualOut 'save-console.log')
    $dualExit=$LASTEXITCODE
    @{exit_code=$dualExit;completed=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dualOut 'save-commandlet.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $dualOut 'save-console.log') -Tail 12
    if($dualExit -ne 0){exit $dualExit}
    & 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe' (Join-Path $dualOut 'publish.py')
    exit $LASTEXITCODE
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$dualSdk
    if($dualHeld){$dualGate.ReleaseMutex()}
    $dualGate.Dispose()
}
