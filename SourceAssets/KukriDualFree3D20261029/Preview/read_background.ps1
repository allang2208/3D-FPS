$ErrorActionPreference='Stop'
$previewRoot='D:\FPS3D\FPSGAME'
$previewOut=Join-Path $previewRoot 'SourceAssets\KukriDualFree3D20261029\Preview'
$previewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$previewHeld=$false
$previewSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $previewHeld=$previewGate.WaitOne([TimeSpan]::FromSeconds(600))
    if(-not $previewHeld){throw 'UE batch occupied; preview read not started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'An editor/game is active; read requires existing bridge.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $previewRoot 'FPSGAME.uproject') '-run=pythonscript' ('-script='+(Join-Path $previewOut 'read_preview_poses.py')) -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile -NoLiveCoding -AssetGatherAll=false -DisablePlugins=FPSDeformationResidency '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' ('-abslog='+(Join-Path $previewOut 'read-engine.log')) -stdout -FullStdOutLogOutput *> (Join-Path $previewOut 'read-console.log')
    $previewExit=$LASTEXITCODE
    Get-Content -LiteralPath (Join-Path $previewOut 'read-console.log') -Tail 12
    exit $previewExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$previewSdk
    if($previewHeld){$previewGate.ReleaseMutex()}
    $previewGate.Dispose()
}
