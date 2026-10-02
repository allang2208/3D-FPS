$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskBuilder='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$taskLogRoot=Join-Path $taskRoot 'Saved/BuildUnarmedPunch20261002'
New-Item -ItemType Directory -Path $taskLogRoot -Force | Out-Null
$taskReceipt=[ordered]@{sourceSaved=$true;animationAssetImportRequired=$false;runtimeTested=$false;rendered=$false;targets=@()}
foreach($taskTarget in @('FPSGAME','FPSGAMEEditor')) {
    $taskWaiting=$false
    while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='MSBuild.exe'" | Where-Object {
        $_.Name -in @('cl.exe','MSBuild.exe') -or $_.CommandLine -match 'UnrealBuildTool'
    }).Count -gt 0) {
        if(!$taskWaiting){Write-Output 'Waiting for the current native build to finish.';$taskWaiting=$true}
        Start-Sleep -Seconds 5
    }
    if($taskTarget -eq 'FPSGAMEEditor') {
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
        })
        if($taskEditors.Count -gt 0){throw 'FPSGAME editor is open; preserve its loaded module and defer the Editor build.'}
    }
    $taskLog=Join-Path $taskLogRoot ($taskTarget+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output "Building $taskTarget in background."
    & $taskBuilder $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$taskLog"
    $taskCode=$LASTEXITCODE
    $taskReceipt.targets+=@{target=$taskTarget;exitCode=$taskCode;log=$taskLog;finishedAt=(Get-Date).ToString('o')}
    $taskReceipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'integration-completion.json') -Encoding UTF8
    if($taskCode -ne 0){throw "$taskTarget build failed. Compiler log: $taskLog"}
    Write-Output "$taskTarget build succeeded."
}
Write-Output 'Both targets saved. No editor/game launch or runtime testing.'
