param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$recoilRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$recoilProject=Join-Path $recoilRoot 'FPSGAME.uproject'
$recoilBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$recoilReceiptFile=Join-Path $PSScriptRoot 'native-build-receipt.json'
$recoilReceipt=if(Test-Path -LiteralPath $recoilReceiptFile){Get-Content -LiteralPath $recoilReceiptFile -Raw | ConvertFrom-Json -AsHashtable}else{@{targets=@{};game_tested=$false}}

# Wait for active asset writers without contacting another task or closing UE.
$reported=$false
while(@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {
    $_.CommandLine -match [regex]::Escape($recoilProject.Replace('/','\'))
}).Count){
    if(-not $reported){Write-Output 'Waiting for current project commandlet to finish.';$reported=$true}
    Start-Sleep -Seconds 15
}
foreach($recoilTarget in $Targets){
    if($recoilTarget -notin @('FPSGAMEEditor','FPSGAME')){throw 'Unexpected build target'}
    $reported=$false
    while(@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }).Count){
        if(-not $reported){Write-Output 'Waiting for active native build to finish.';$reported=$true}
        Start-Sleep -Seconds 15
    }
    $recoilEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        $_.CommandLine -match [regex]::Escape($recoilProject.Replace('/','\')) -or
        $_.CommandLine -match [regex]::Escape($recoilProject.Replace('\','/'))
    })
    if($recoilTarget -eq 'FPSGAMEEditor' -and $recoilEditors.Count){throw 'FPSGAME editor/commandlet is open. No process was closed; native build deferred.'}
    if($recoilTarget -eq 'FPSGAME' -and @(Get-Process -Name 'FPSGAME' -ErrorAction SilentlyContinue).Count){throw 'Standalone game is running; preserve its executable.'}
    $recoilLog=Join-Path $PSScriptRoot ("build-$recoilTarget-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output "Building $recoilTarget. Log: $recoilLog"
    & $recoilBuild $recoilTarget Win64 Development "-project=$recoilProject" -NoHotReloadFromIDE *> $recoilLog
    $recoilCode=$LASTEXITCODE
    $recoilReceipt.targets[$recoilTarget]=@{exit_code=$recoilCode;log=$recoilLog;curve_sha256=(Get-FileHash -LiteralPath (Join-Path $recoilRoot 'Source/FPSGAME/Weapons/RifleAxialRecoil.h') -Algorithm SHA256).Hash}
    $recoilReceipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recoilReceiptFile -Encoding UTF8
    Get-Content -LiteralPath $recoilLog -Tail 10
    if($recoilCode -ne 0){throw "Build failed: $recoilLog"}
}
