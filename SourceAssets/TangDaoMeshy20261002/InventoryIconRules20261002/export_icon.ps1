param([int]$QueueWaitSeconds=600)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$projectRoot=[IO.Path]::GetFullPath((Join-Path $taskRoot '../../..'))
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $held=$true;throw 'Previous UE batch ended unexpectedly; icon authoring was not run.' }
    if (-not $held) { throw 'UE batch lock is busy; icon authoring was not run.' }
    $before=Join-Path $taskRoot 'Before'
    [IO.Directory]::CreateDirectory($before) | Out-Null
    foreach ($name in @('ue_tang_dao','ue_tang_dao_surface_v2')) {
        foreach ($suffix in @('.png','.uasset')) {
            $source=Join-Path $projectRoot ('Content/ColdSteelData/Icons/'+$name+$suffix)
            $backup=Join-Path $before ($name+$suffix)
            if ((Test-Path -LiteralPath $source) -and -not (Test-Path -LiteralPath $backup)) {
                Copy-Item -LiteralPath $source -Destination $backup
            }
        }
    }
    # Read saved UE assembly and materials. Write this catalog PNG only;
    # do not save UE packages or initialize a gameplay/profile session.
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $log=Join-Path $taskRoot ('export-'+$stamp+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        (Join-Path $projectRoot 'FPSGAME.uproject') -run=ColdSteelWeaponIconCatalog -Definition=ue_tang_dao `
        -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound `
        "-abslog=$log" *> (Join-Path $taskRoot ('export-'+$stamp+'-console.log'))
    $engineExit=$LASTEXITCODE
    if ($engineExit -ne 0) { throw "TangDao icon authoring process failed ($engineExit); see $log" }
    if (-not (Select-String -LiteralPath $log -SimpleMatch 'WeaponIconCatalog: COMPLETE failures=0' -Quiet)) {
        throw "TangDao icon authoring did not complete; see $log"
    }
    $produced=Join-Path $projectRoot 'Content/ColdSteelData/Icons/ue_tang_dao.png'
    Copy-Item -LiteralPath $produced -Destination (Join-Path $taskRoot 'ue_tang_dao.png')
    $familyRoot=Split-Path -Parent $taskRoot
    foreach ($folder in @('Icons','SurfaceV2/Icons')) {
        $destination=Join-Path $familyRoot ($folder+'/ue_tang_dao.png')
        Copy-Item -LiteralPath $produced -Destination $destination
    }
    $manifest=@{
        definition='ue_tang_dao';source='ColdSteelWeaponIconCatalog: saved UE factory assembly and game materials';
        render_log=$log;engine_exit=$engineExit;runtime_tested=$false;
        png=(Join-Path $taskRoot 'ue_tang_dao.png');sha256=(Get-FileHash -LiteralPath $produced -Algorithm SHA256).Hash;
        orientation='portrait; blade tip up; orthographic side view';size=@(384,768);alpha='transparent';
        rules='Docs/UI/ui-cold-steel-design-system.md section 7; ColdSteelMeleeIcon.cpp'
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskRoot 'export_receipt.json') -Encoding UTF8
    Write-Output 'TANGDAO_INVENTORY_ICON_AUTHORED 384x768'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
