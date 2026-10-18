$ErrorActionPreference='Stop'
$m870ReviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$m870ReviewHeld=$false
$m870ReviewSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $m870ReviewHeld=$m870ReviewGate.WaitOne([TimeSpan]::FromMinutes(15))
    if(-not $m870ReviewHeld){throw 'Existing UE batch remained busy; no operation launched.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' *> (Join-Path $PSScriptRoot 'build-editor.log')
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor.log') -Tail 7
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=ShotgunAttachmentAudit -M870Presentation `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile `
        '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $PSScriptRoot 'audit-engine.log')) -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot 'audit-console.log')
    $m870ReviewExit=$LASTEXITCODE
    @{exit_code=$m870ReviewExit;finished=(Get-Date).ToString('s');mode='isolated presentation audit; no socket transport';asset_writes=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'audit-receipt.json') -Encoding utf8
    Copy-Item -LiteralPath 'D:/FPS3D/FPSGAME/Saved/M870ThirdPersonReview20261018/result.json' -Destination (Join-Path $PSScriptRoot 'result.json')
    $m870ReviewResult=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'result.json') -Raw | ConvertFrom-Json
    Write-Output "M870 presentation checks=$($m870ReviewResult.checks) failures=$($m870ReviewResult.failures) exit=$m870ReviewExit"
    exit $m870ReviewExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$m870ReviewSdk
    if($m870ReviewHeld){$m870ReviewGate.ReleaseMutex()};$m870ReviewGate.Dispose()
}
