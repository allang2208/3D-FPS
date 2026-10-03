$ErrorActionPreference='Stop'
$partRoot=$PSScriptRoot
$projectRoot=[IO.Path]::GetFullPath((Join-Path $partRoot '../../..'))
$engineRoot='E:/Program Files (x86)/UE_5.8'
$state=@{editor_built=$false;game_built=$false;editor_launched=$false;runtime_tested=$false;complete=$false}
function Save-BuildState {
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $partRoot 'build_receipt.json') -Encoding utf8
}
function Wait-ExistingBuild {
    $reported=$false
    while ($true) {
        $builds=Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='UnrealBuildTool.exe' OR Name='cl.exe'" | Where-Object { $_.Name -eq 'cl.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or $_.CommandLine -like '*UnrealBuildTool*' }
        if (-not $builds) {return}
        if (-not $reported) {Write-Output 'Waiting for the existing native build to finish before this build.';$reported=$true}
        Start-Sleep -Seconds 5
    }
}
Save-BuildState
foreach ($entry in @(@{target='FPSGAMEEditor';key='editor_built';label='editor'},@{target='FPSGAME';key='game_built';label='game'})) {
    Wait-ExistingBuild
    if ($entry.target -eq 'FPSGAMEEditor' -and (Get-Process UnrealEditor -ErrorAction SilentlyContinue)) {
        $state['blocked_reason']='An existing editor occupies the native editor binary; its session was preserved.';Save-BuildState
        Write-Output $state.blocked_reason;exit 76
    }
    $logPath=Join-Path $partRoot ('build-'+$entry.label+'.log')
    & (Join-Path $engineRoot 'Engine/Build/BatchFiles/Build.bat') $entry.target Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -NoHotReloadFromIDE "-Log=$logPath" *> (Join-Path $partRoot ('build-'+$entry.label+'-console.log'))
    $code=$LASTEXITCODE
    $state[$entry.key]=($code -eq 0);$state[$entry.label+'_exit_code']=$code;Save-BuildState
    if ($code -ne 0) {Write-Output ('Native build failed: '+$entry.target);exit $code}
    Write-Output ('Built and saved '+$entry.target)
}
$state.complete=$true;Save-BuildState
Write-Output 'PHOENIX_GUARD_GOLD_CARD_BINARIES_SAVED'
