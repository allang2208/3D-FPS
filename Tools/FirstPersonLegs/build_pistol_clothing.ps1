$ErrorActionPreference = 'Stop'
$legProject = 'D:/FPS3D/FPSGAME'
$legOutput = "$legProject/SourceAssets/PistolClothingRepair20261006"
New-Item -ItemType Directory -Force -Path $legOutput | Out-Null
$legDeadline = [DateTime]::UtcNow.AddMinutes(40)
$legWaiting = $false
while ($true) {
    $legProcesses = Get-CimInstance Win32_Process
    $legEditor = $legProcesses | Where-Object { $_.Name -in @('UnrealEditor.exe','FPSGAME.exe') -and $_.CommandLine -match 'FPSGAME' }
    if ($legEditor) { throw 'FPSGAME is open; preserve its session and close it before the normal DLL build.' }
    $legBusy = $legProcesses | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')
    }
    if (-not $legBusy) { break }
    if (-not $legWaiting) { Write-Output 'Waiting for the active build/commandlet before submitting the shared owner body build.'; $legWaiting = $true }
    if ([DateTime]::UtcNow -gt $legDeadline) { throw 'Project build remains occupied; no competing build submitted.' }
    Start-Sleep -Seconds 15
}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$legProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$legOutput/build-editor.log" *> "$legOutput/build-editor-console.txt"
if ($LASTEXITCODE -ne 0) { throw "Shared owner body build failed ($LASTEXITCODE). See $legOutput/build-editor.log" }
Write-Output 'PISTOL_CLOTHING_EDITOR_BUILT'
