$ErrorActionPreference='Stop'
$freeRoot='D:\FPS3D\FPSGAME'
$freeOut=Join-Path $freeRoot 'SourceAssets\KukriDualFree3D20261029'
$freeProject=Join-Path $freeRoot 'FPSGAME.uproject'
$freeGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$freeHeld=$false
$freeSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $freeHeld=$freeGate.WaitOne([TimeSpan]::FromSeconds(600))
    if(-not $freeHeld){throw 'UE batch is occupied; no asset write started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'An editor/game is active; leaving its assets unchanged.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $freeProject '-run=pythonscript' ('-script='+(Join-Path $freeOut 'save_all.py')) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile -NoLiveCoding -AssetGatherAll=false `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $freeOut 'save-engine.log')) -stdout -FullStdOutLogOutput *> (Join-Path $freeOut 'save-console.log')
    $freeExit=$LASTEXITCODE
    @{exit_code=$freeExit;completed=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $freeOut 'save-commandlet.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $freeOut 'save-console.log') -Tail 12
    if($freeExit -ne 0){exit $freeExit}
    & 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe' (Join-Path $freeOut 'publish.py')
    exit $LASTEXITCODE
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$freeSdk
    if($freeHeld){$freeGate.ReleaseMutex()}
    $freeGate.Dispose()
}
