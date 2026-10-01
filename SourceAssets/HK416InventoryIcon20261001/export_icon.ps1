param([string]$Label='export')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$projectRoot='D:\FPS3D\FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$priorSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while(-not $held) {
        try {$held=$gate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if(-not $held){Write-Output 'Waiting for the icon authoring batch lock.'}
    }
    # This production export reads saved meshes/materials and writes only the
    # requested catalog PNG. It never saves or replaces loaded UE packages.
    $previous=Join-Path $taskRoot 'ue_hk416_previous.png'
    if(-not (Test-Path -LiteralPath $previous)) {
        Copy-Item -LiteralPath "$projectRoot\Content\ColdSteelData\Icons\ue_hk416.png" -Destination $previous
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
        "$projectRoot\FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_hk416 `
        -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot\$Label-commandlet.log"
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
    Copy-Item -LiteralPath "$projectRoot\Content\ColdSteelData\Icons\ue_hk416.png" -Destination "$taskRoot\ue_hk416.png"
} finally {$env:UE_SKIP_UBT_SDK_SETUP=$priorSdk;if($held){$gate.ReleaseMutex()};$gate.Dispose()}
