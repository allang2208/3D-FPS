$ErrorActionPreference='Stop'
$root='D:\FPS3D\FPSGAME'
$taskRoot=$PSScriptRoot
function Get-ActiveBuild {
    @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
}
if((Get-ActiveBuild).Count -gt 0){Write-Output 'Waiting for the current native build to finish before submitting the HK416 build.'}
while((Get-ActiveBuild).Count -gt 0){Start-Sleep -Seconds 15}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$held=$true}
    while(-not $held){try {$held=$gate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$held=$true}}
    if((Get-ActiveBuild).Count -gt 0){throw 'A native build started before this batch obtained its lock; no competing build was submitted.'}
    $editors=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'"
    if($editors | Where-Object {$_.CommandLine -like '*FPSGAME*'}){throw 'FPSGAME editor/game/commandlet is active; preserve it and do not link over loaded modules.'}
    Write-Output 'Building the HK416 optical-sight visibility change.'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development `
        '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 `
        "-Log=$taskRoot\build-editor.log" *> "$taskRoot\build-console.log"
    if($LASTEXITCODE -ne 0){throw "Native build failed with exit code $LASTEXITCODE; see build-editor.log."}
    Write-Output 'Editor module build completed.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
& "$taskRoot\run_commandlet.ps1" -Script import_assets.py -Label import-after-build *> "$taskRoot\import-after-build-console.log"
exit $LASTEXITCODE
