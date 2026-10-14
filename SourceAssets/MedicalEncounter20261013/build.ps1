$ErrorActionPreference='Stop'
$medicalProject='D:\FPS3D\FPSGAME'
$medicalBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$medicalReceipts=Join-Path $PSScriptRoot 'Receipts'
$medicalWaiting=$false
foreach($medicalTarget in @('FPSGAMEEditor','FPSGAME')) {
    while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe'" | Where-Object { $_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool' }).Count -gt 0) {
        if(-not $medicalWaiting){Write-Output 'Waiting for the active native build to finish.';$medicalWaiting=$true}
        Start-Sleep -Seconds 15
    }
    $medicalEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match '(?i)D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject' })
    if($medicalEditors.Count){throw 'The project editor/commandlet is running; preserve that process before linking.'}
    $medicalStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $medicalLog=Join-Path $medicalReceipts ("build-$medicalTarget-$medicalStamp.log")
    Write-Output "BUILD_STARTED $medicalTarget LOG=$medicalLog"
    & $medicalBuild $medicalTarget Win64 Development "-Project=$medicalProject\FPSGAME.uproject" '-NoHotReloadFromIDE' *> $medicalLog
    $medicalCode=$LASTEXITCODE
    @{target=$medicalTarget;exit_code=$medicalCode;log=$medicalLog;finished=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $medicalReceipts ("build-$medicalTarget.json")) -Encoding utf8
    Write-Output "BUILD_FINISHED $medicalTarget EXIT=$medicalCode LOG=$medicalLog"
    if($medicalCode -ne 0){throw "Native build failed: $medicalLog"}
}