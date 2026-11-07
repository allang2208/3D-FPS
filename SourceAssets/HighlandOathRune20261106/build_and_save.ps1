param([switch]$AssetsOnly)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/Saved/HighlandOathRune20261106"
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; no build or asset write started.'}
    $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
    foreach($taskBuild in $taskBuilds){try{[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()}catch [ArgumentException]{}}
    $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'})
    if($taskOwners.Count){throw 'Preserving running FPSGAME editor; build/import not started.'}
    if(-not $AssetsOnly){
        $taskModes=@()
        $taskDefines="$taskRoot/Intermediate/Build/Win64/x64/FPSGAMEEditor/Development/Core/SharedDefinitions.Core.Cpp20.h"
        if((Test-Path -LiteralPath $taskDefines) -and [IO.File]::ReadAllText($taskDefines) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$taskModes+='-NoLiveCoding'}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE @taskModes -MaxParallelActions=4 "-Log=$taskOut/build.log" *> "$taskOut/build-console.log"
        if($LASTEXITCODE -ne 0){throw "Build failed; see $taskOut/build.log"}
        Write-Output 'Oath editor build completed.'
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/install_assets.py" -NullRHI -Unattended -NoSplash -NoSound -nop4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$taskOut/import.log" *> "$taskOut/import-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset import failed; see $taskOut/import.log"}
    Write-Output 'Oath production assets saved; no gameplay tests run.'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
