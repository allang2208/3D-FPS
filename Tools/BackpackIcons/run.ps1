param([string[]]$Definitions=@(),[string]$OutputGroup='Catalog',[switch]$SaveDisplay)
$ErrorActionPreference='Stop'
$packProject='D:/FPS3D/FPSGAME'
$packRoot=Join-Path $packProject 'SourceAssets/BackpackIcons20261025/FrontR1'
$packPlan=Get-Content -LiteralPath "$packRoot/plan.json" -Raw -Encoding utf8 | ConvertFrom-Json
if(-not $Definitions.Count){$Definitions=@($packPlan.items | ForEach-Object {$_.id})}
foreach($packId in $Definitions){if($packId -notmatch '^ue_[a-z_]+$'){throw 'Invalid backpack definition'}}
if($OutputGroup -notmatch '^[A-Za-z0-9_-]+$'){throw 'Invalid output folder'}
$packOutput=Join-Path $packRoot $OutputGroup
New-Item -ItemType Directory -Path $packOutput -Force | Out-Null
$packGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$packHeld=$false
try {
    try{$packHeld=$packGate.WaitOne()}catch [Threading.AbandonedMutexException]{$packHeld=$true}
    while($true){
        $packBusy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'D:[\/]FPS3D[\/]FPSGAME')})
        if(-not $packBusy.Count){break}
        try{Wait-Process -Id $packBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $packBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $packLog=Join-Path $packOutput ('author-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    $packArgs=@("$packProject/FPSGAME.uproject",'-unattended','-nop4','-nosplash','-nosound',('-abslog='+$packLog))
    if($SaveDisplay){$packArgs+=@('-run=pythonscript',('-script='+$packProject+'/Tools/BackpackIcons/save_display.py'),'-nullrhi')}
    else {$packArgs+=@('-run=ColdSteelWeaponIconCatalog',('-Definitions="'+($Definitions -join ',')+'"'),('-OutputDirectory='+$packOutput),'-RenderOffscreen','-AllowCommandletRendering','-d3d12','-NoTextureStreaming')}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @packArgs *> ($packLog+'.stdout.txt')
    $packCode=$LASTEXITCODE
    @{stage=$(if($SaveDisplay){'save_display'}else{'catalog_export'});exit_code=$packCode;definitions=$Definitions;log=$packLog;output=$packOutput;gameplay_tested=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $packOutput 'author-receipt.json') -Encoding utf8
    Get-Content -LiteralPath ($packLog+'.stdout.txt') -Tail 7
    if($packCode -ne 0){throw "Backpack authoring failed: $packLog"}
    if($SaveDisplay){
        & python "$packProject/Tools/BackpackIcons/publish_display.py"
        if($LASTEXITCODE -ne 0){throw 'Display reference publication failed'}
    }
    if(-not $SaveDisplay -and $OutputGroup -eq 'Catalog'){
        & python "$packProject/Tools/BackpackIcons/publish.py" --definitions ($Definitions -join ',') --directory $packOutput
        if($LASTEXITCODE -ne 0){throw 'Catalog PNG publication failed'}
    }
}finally{if($packHeld){$packGate.ReleaseMutex()};$packGate.Dispose()}
