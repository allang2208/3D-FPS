param()
$ErrorActionPreference='Stop'
$taskRoot='D:\FPS3D\FPSGAME'
$taskReceipt=Join-Path $PSScriptRoot 'Receipts/native-build.json'
$taskLog=Join-Path $PSScriptRoot ('Receipts/native-build-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$taskDeadline=(Get-Date).AddMinutes(45)
@{stage='waiting_for_build_window';log=$taskLog} | ConvertTo-Json | Set-Content -LiteralPath $taskReceipt -Encoding UTF8
Write-Output 'Waiting for existing UE/build processes to finish; no processes will be stopped.'
while ($true) {
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -like 'UnrealEditor*' -and $_.CommandLine -like '*FPSGAME*') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*') -or
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe')
    })
    if ($taskBusy.Count -eq 0) { break }
    if ((Get-Date) -gt $taskDeadline) { throw 'Build window remains occupied; source and assets were preserved.' }
    foreach ($taskItem in $taskBusy) {
        $taskProcess=Get-Process -Id $taskItem.ProcessId -ErrorAction SilentlyContinue
        if ($taskProcess) { [void]$taskProcess.WaitForExit(5000) }
    }
}
@{stage='building';log=$taskLog} | ConvertTo-Json | Set-Content -LiteralPath $taskReceipt -Encoding UTF8
Write-Output "DUNGEON_SPAWN_RESET_BUILD_STARTED LOG=$taskLog"
try {
    $taskOldSDK=$env:UE_SKIP_UBT_SDK_SETUP
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & (Join-Path $taskRoot 'Tools/Build/Build-Editor.ps1') *> $taskLog
    if ($LASTEXITCODE -ne 0) { throw "Native build exit $LASTEXITCODE" }
    $taskDll=Get-Item (Join-Path $taskRoot 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
    @{stage='build_succeeded';log=$taskLog;dll=$taskDll.FullName;dll_write_utc=$taskDll.LastWriteTimeUtc.ToString('o');runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath $taskReceipt -Encoding UTF8
    Write-Output 'DUNGEON_SPAWN_RESET_BUILD_SUCCEEDED'
} catch {
    @{stage='build_failed';log=$taskLog;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $taskReceipt -Encoding UTF8
    throw
} finally { $env:UE_SKIP_UBT_SDK_SETUP=$taskOldSDK }
& (Join-Path $PSScriptRoot 'run_background.ps1')
