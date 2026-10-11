param()
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskReport=@{game_tested=$false;targets=@{}}
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')){
    $reported=$false
    while(@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }).Count){
        if(-not $reported){Write-Output 'Waiting for the current native build or commandlet.';$reported=$true}
        Start-Sleep -Seconds 15
    }
    if(@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='FPSGAME.exe'" | Where-Object {
        $_.Name -eq 'FPSGAME.exe' -or [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    }).Count){throw 'Editor or game opened; preserve the active process and defer DLL replacement.'}
    $taskLog=Join-Path $PSScriptRoot ("build-$taskTarget-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output "Building $taskTarget. Log: $taskLog"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-project=$taskProject/FPSGAME.uproject" -NoHotReloadFromIDE *> $taskLog
    $taskCode=$LASTEXITCODE
    $taskReport.targets[$taskTarget]=@{exit_code=$taskCode;log=$taskLog}
    $taskReport | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'native-build-receipt.json') -Encoding UTF8
    Get-Content -LiteralPath $taskLog -Tail 12
    if($taskCode -ne 0){throw "Native build failed: $taskLog"}
}
