param([int]$QueueWaitSeconds=1800)
$ErrorActionPreference='Stop'
$knifeReviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$knifeReviewHeld=$false
try {
    $knifeReviewHeld=$knifeReviewGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))
    if(-not $knifeReviewHeld){throw 'UE batch occupied; review not started.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=ShotgunAttachmentAudit -PistolBody -OffhandKnife `
        ('-Output='+(Join-Path $PSScriptRoot 'pose-review.json')) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile -AssetGatherAll=false `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $PSScriptRoot 'review-engine.log')) -stdout -FullStdOutLogOutput `
        *> (Join-Path $PSScriptRoot 'review-console.log')
    $knifeReviewExit=$LASTEXITCODE
    @{exit_code=$knifeReviewExit;completed=(Get-Date).ToString('o')} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot 'review-commandlet.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'review-console.log') -Tail 5
    exit $knifeReviewExit
} finally {
    if($knifeReviewHeld){$knifeReviewGate.ReleaseMutex()}
    $knifeReviewGate.Dispose()
}
