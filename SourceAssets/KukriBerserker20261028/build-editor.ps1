$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskDeadline=(Get-Date).AddMinutes(20)
while ((Get-Date) -lt $taskDeadline) {
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match '^UnrealEditor.*\.exe$' -and $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($taskProject)) -or
        ($_.Name -eq 'FPSGAME.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -in @('UnrealBuildTool.exe','cl.exe'))
    })
    if ($taskBusy.Count -gt 0) {
        Write-Output ('Waiting for module users or current build: '+(($taskBusy | ForEach-Object {$_.ProcessId}) -join ','))
        Wait-Process -Id $taskBusy.ProcessId -Timeout 45 -ErrorAction SilentlyContinue
        continue
    }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskProject" -NoHotReloadFromIDE -WaitMutex *> (Join-Path $PSScriptRoot 'build-editor.log')
    $taskExit=$LASTEXITCODE
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor.log') -Tail 22
    exit $taskExit
}
throw 'The editor or another build is still using the module. Sources are saved; the base Editor DLL is not updated.'
