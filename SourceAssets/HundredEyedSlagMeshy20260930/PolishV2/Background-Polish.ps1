param([int]$WaitSeconds=3600)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=Join-Path $projectRoot 'SourceAssets\HundredEyedSlagMeshy20260930\PolishV2'
$engineRoot='E:\Program Files (x86)\UE_5.8'
$deadline=(Get-Date).AddSeconds($WaitSeconds)
function Wait-ForProjectRelease {
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and
            ($_.CommandLine -match 'FPSGAME[\\/]FPSGAME.uproject' -or [string]::IsNullOrWhiteSpace($_.CommandLine))
        })
        if(-not $busy.Count){return}
        if((Get-Date) -ge $deadline){throw 'Background wait expired; all other UE processes preserved.'}
        Start-Sleep -Seconds 10
    } while($true)
}
# Keep the established bridge gate for this entire editor/commandlet batch.
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds($WaitSeconds))} catch [Threading.AbandonedMutexException] {$held=$true; throw 'Abandoned UE operation; preserve unknown state.'}
    if(-not $held){throw 'UE bridge queue expired.'}
    Wait-ForProjectRelease
    Set-Location -LiteralPath $projectRoot
    & (Join-Path $engineRoot 'Engine\Build\BatchFiles\Build.bat') FPSGAMEEditor Win64 Development ('-Project='+$projectRoot+'\FPSGAME.uproject') -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -DisableUnity ('-Log='+$out+'\build_nonunity.log') *> (Join-Path $out 'build_nonunity_console.txt')
    if($LASTEXITCODE -ne 0){throw 'Native build failed; see build_nonunity_console.txt'}
    # Actual import, compilation and package save with rendering resources, no UI window.
    & (Join-Path $engineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe') ($projectRoot+'\FPSGAME.uproject') -run=pythonscript ('-script='+$out+'\install_polish.py') -unattended -nop4 -nosplash -nosound -d3d12 -AllowCommandletRendering -RenderOffscreen ('-abslog='+$out+'\install_commandlet.log') *> (Join-Path $out 'install_commandlet_console.txt')
    if($LASTEXITCODE -ne 0){throw 'Asset commandlet failed; see install_commandlet.log'}
    & (Join-Path $engineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe') ($projectRoot+'\FPSGAME.uproject') -run=pythonscript ('-script='+$out+'\check_saved_ue.py') -unattended -nop4 -nosplash -nosound -d3d12 -AllowCommandletRendering -RenderOffscreen ('-abslog='+$out+'\saved_readback.log') *> (Join-Path $out 'saved_readback_console.txt')
    if($LASTEXITCODE -ne 0){throw 'Saved asset readback failed; see saved_readback.log'}
    @{stage='native_build_and_actual_polish_assets_saved';completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'build_receipt.json') -Encoding UTF8
    Write-Output 'SLAG_POLISH_BUILD_AND_IMPORT_COMPLETE'
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
