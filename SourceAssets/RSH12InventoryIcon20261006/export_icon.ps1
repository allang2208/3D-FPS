param([string]$Label='export')
$ErrorActionPreference='Stop'
$rshProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$rshEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
# This standalone image-production pass reads saved packages and exports only
# this task's PNG. UE package import/save is a separate mutex-protected batch.
& {
    $rshIcon=Join-Path $rshProject 'Content/ColdSteelData/Icons/ue_rsh12.png'
    $rshBefore=Join-Path $PSScriptRoot 'ue_rsh12_previous.png'
    if((Test-Path -LiteralPath $rshIcon) -and -not (Test-Path -LiteralPath $rshBefore)){
        Copy-Item -LiteralPath $rshIcon -Destination $rshBefore
    }
    # Read only saved UE packages; write the requested catalog PNG. No package,
    # live editor state, game world or player profile is saved by this commandlet.
    $rshLog=Join-Path $PSScriptRoot "$Label-commandlet.log"
    & $rshEngine "$rshProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_rsh12 -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$rshLog" *> "$PSScriptRoot/$Label-console.txt"
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath "$PSScriptRoot/$Label-console.txt" -Tail 10;throw "RSH icon export failed: $rshLog"}
    Copy-Item -LiteralPath $rshIcon -Destination "$PSScriptRoot/ue_rsh12.png"
    Write-Output "RSH12_INVENTORY_ICON_EXPORTED $rshLog"
}
