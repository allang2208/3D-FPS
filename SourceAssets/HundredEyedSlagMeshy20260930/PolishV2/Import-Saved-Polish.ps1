$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=Join-Path $projectRoot 'SourceAssets\HundredEyedSlagMeshy20260930\PolishV2'
$cmdExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true;throw 'Abandoned UE batch; no operations sent.'}
    if(-not $held){throw 'UE batch queue expired'}
    $deadline=(Get-Date).AddMinutes(30)
    while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME[\\/]FPSGAME.uproject' }).Count){
        if((Get-Date) -gt $deadline){throw 'Loaded UE process still busy'}
        Start-Sleep -Seconds 10
    }
    foreach($step in @('install_polish','check_saved_ue')){
        & $cmdExe ($projectRoot+'\FPSGAME.uproject') -run=pythonscript ('-script='+$out+'\'+$step+'.py') -unattended -nop4 -nosplash -nosound -d3d12 -AllowCommandletRendering -RenderOffscreen ('-abslog='+$out+'\'+$step+'_rhi.log') *> (Join-Path $out ($step+'_rhi_console.txt'))
        if($LASTEXITCODE -ne 0){throw ($step+' commandlet failed')}
    }
    @{stage='native_build_and_actual_polish_assets_saved';completed=(Get-Date).ToString('o');native_build='build_nonunity.log';readback='saved_ue_checks.json'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'build_receipt.json') -Encoding UTF8
    Write-Output 'SLAG_POLISH_BUILD_IMPORT_AND_SAVED_READBACK_COMPLETE'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
