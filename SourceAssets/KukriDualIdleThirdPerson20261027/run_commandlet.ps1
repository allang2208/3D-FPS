param([Parameter(Mandatory=$true)][ValidateSet('prepare','save_all')][string]$Stage,[int]$QueueWaitSeconds=600)
$ErrorActionPreference='Stop'
$kukriRoot='D:\FPS3D\FPSGAME'
$kukriGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$kukriHeld=$false
$kukriSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $kukriHeld=$kukriGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
    if(-not $kukriHeld){throw 'UE asset batch is occupied; no operation sent.'}
    $projectFile=Join-Path $kukriRoot 'FPSGAME.uproject'
    $editors=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and
        (-not $_.CommandLine -or $_.CommandLine.Replace('/','\').IndexOf($projectFile,[StringComparison]::OrdinalIgnoreCase) -ge 0)
    })
    if($editors.Count -and $Stage -ne 'prepare'){throw 'An editor is running; no background asset operation submitted.'}
    # prepare reads saved sequences only; it never writes packages or operates on a running world.
    # Write only new DualIdleV1 packages; every existing package is read-only.
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
        (Join-Path $kukriRoot 'FPSGAME.uproject') '-run=pythonscript' ('-script='+(Join-Path $PSScriptRoot ($Stage+'.py'))) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile -AssetGatherAll=false `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $PSScriptRoot ($Stage+'-engine.log'))) -stdout -FullStdOutLogOutput `
        *> (Join-Path $PSScriptRoot ($Stage+'-console.log'))
    $kukriExit=$LASTEXITCODE
    @{exit_code=$kukriExit;stage=$Stage;completed=(Get-Date).ToString('o')} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot ($Stage+'-commandlet.json')) -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Stage+'-console.log')) -Tail 14
    exit $kukriExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$kukriSdk
    if($kukriHeld){$kukriGate.ReleaseMutex()}
    $kukriGate.Dispose()
}
