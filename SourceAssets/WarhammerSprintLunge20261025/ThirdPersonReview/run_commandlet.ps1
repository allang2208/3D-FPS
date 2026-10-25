param([Parameter(Mandatory=$true)][string]$Stage,[int]$QueueWaitSeconds=900,[switch]$IndependentAssets)
$ErrorActionPreference='Stop'
$hammerRoot='D:\FPS3D\FPSGAME'
$hammerScript=Join-Path $PSScriptRoot ($Stage+'.py')
$hammerGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$hammerHeld=$false
$hammerSdkSetting=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $hammerHeld=$hammerGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
    if(-not $hammerHeld){throw 'UE asset batch is busy; no operation sent.'}
    if($IndependentAssets -and $Stage -notin @('prepare_sources','save_actions','prepare_sprint_lift','save_sprint_lift','save_normal_combo','prepare_heavy_uppercut','save_heavy_uppercut','save_direct_kwang','prepare_secondary_donors','save_secondary_donors','save_anatomical_grip','save_refinement_v8','save_carry_sprint_v10','prepare_locomotion_v11','save_locomotion_v11','prepare_centered_carry_v12','save_centered_carry_v12','save_relaxed_grip_v13','prepare_fp_hold_v14','save_fp_ready_v14','prepare_source_carry_v15','save_source_carry_v15','save_source_grip_v16','save_natural_combo_v17','save_slash3_alignment_v18')){
        throw 'Independent mode is limited to this batch exclusive new animation packages.'
    }
    if(-not $IndependentAssets -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'")){
        # The mutex is recursive on this same PowerShell thread. Route through
        # the established bridge if an editor appeared while we were queued.
        & (Join-Path $hammerRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') `
            -PythonScript $hammerScript -QueueWaitSeconds 0 `
            -OutputFile (Join-Path $PSScriptRoot ($Stage+'-bridge-'+(Get-Date -Format 'HHmmssfff')+'.log')) `
            -MaxOutputChars 6000
        exit $LASTEXITCODE
    }
    # Asset-only production does not need UBT's platform SDK discovery. UE's
    # supported switch avoids its synchronous startup wait on the build lock.
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $hammerLog=Join-Path $PSScriptRoot ($Stage+'-engine.log')
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
       (Join-Path $hammerRoot 'FPSGAME.uproject') '-run=pythonscript' ('-script='+$hammerScript) `
       -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile `
       '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
       ('-abslog='+$hammerLog) -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot ($Stage+'-console.log'))
    $hammerExit=$LASTEXITCODE
    @{exit_code=$hammerExit;log=$hammerLog;finished=(Get-Date).ToString('s')} | ConvertTo-Json |
       Set-Content -LiteralPath (Join-Path $PSScriptRoot ($Stage+'-commandlet.json')) -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Stage+'-console.log')) -Tail 14
    exit $hammerExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$hammerSdkSetting
    if($hammerHeld){$hammerGate.ReleaseMutex()}
    $hammerGate.Dispose()
}
