param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$casingRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$casingProject=Join-Path $casingRoot 'FPSGAME.uproject'
$casingBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$casingReceiptFile=Join-Path $PSScriptRoot 'native-build-receipt.json'
$reported=$false
while(@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {
    $_.CommandLine -match [regex]::Escape($casingProject.Replace('/','\')) -or
    $_.CommandLine -match [regex]::Escape($casingProject.Replace('\','/'))
}).Count){
    if(-not $reported){Write-Output 'Waiting for the current project commandlet.';$reported=$true}
    Start-Sleep -Seconds 15
}
foreach($casingTarget in $Targets){
    if($casingTarget -notin @('FPSGAMEEditor','FPSGAME')){throw 'Unexpected build target'}
    $reported=$false
    while(@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }).Count){
        if(-not $reported){Write-Output 'Waiting for the active native build.';$reported=$true}
        Start-Sleep -Seconds 15
    }
    $casingEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        $_.CommandLine -match [regex]::Escape($casingProject.Replace('/','\')) -or
        $_.CommandLine -match [regex]::Escape($casingProject.Replace('\','/'))
    })
    if($casingTarget -eq 'FPSGAMEEditor' -and $casingEditors.Count){throw 'Editor is open; native DLL build deferred. No process was closed.'}
    if($casingTarget -eq 'FPSGAME' -and @(Get-Process -Name 'FPSGAME' -ErrorAction SilentlyContinue).Count){throw 'Standalone game is running; preserve its executable.'}
    $casingLog=Join-Path $PSScriptRoot ("build-$casingTarget-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output "Building $casingTarget. Log: $casingLog"
    & $casingBuild $casingTarget Win64 Development "-project=$casingProject" -NoHotReloadFromIDE *> $casingLog
    $casingCode=$LASTEXITCODE
    $casingHashes=@{}
    foreach($casingFile in @('FPSWeaponFXComponent.cpp','FPSWeaponFXComponent.h','CasingPortCalibration.h')){
        $casingHashes[$casingFile]=(Get-FileHash -LiteralPath (Join-Path $casingRoot "Source/FPSGAME/Weapons/$casingFile") -Algorithm SHA256).Hash
    }
    $casingReceipt=if(Test-Path -LiteralPath $casingReceiptFile){Get-Content -LiteralPath $casingReceiptFile -Raw | ConvertFrom-Json -AsHashtable}else{@{targets=@{};game_tested=$false}}
    $casingReceipt.targets[$casingTarget]=@{exit_code=$casingCode;log=$casingLog;source_sha256=$casingHashes}
    $casingReceipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $casingReceiptFile -Encoding UTF8
    Get-Content -LiteralPath $casingLog -Tail 12
    if($casingCode -ne 0){throw "Build failed: $casingLog"}
}
