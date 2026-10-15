param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $PSScriptRoot 'Receipts'
$taskResults=@()
if(Test-Path -LiteralPath (Join-Path $taskOutput 'build.json')) {
    $taskPrevious=Get-Content -LiteralPath (Join-Path $taskOutput 'build.json') -Raw | ConvertFrom-Json
    $taskResults=@($taskPrevious.results | Where-Object {$_.target -notin $Targets})
}
foreach($taskTarget in $Targets) {
    $taskPriorBuilds=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
    foreach($taskPrior in $taskPriorBuilds) {
        Write-Output "Waiting for existing build PID $($taskPrior.ProcessId)"
        try {[Diagnostics.Process]::GetProcessById($taskPrior.ProcessId).WaitForExit()} catch [ArgumentException] {}
    }
    # Game builds do not replace the editor DLL loaded by an asset commandlet.
    $taskBackground=@()
    if($taskTarget -eq 'FPSGAMEEditor') {
        $taskBackground=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject") })
    }
    foreach($taskPrior in $taskBackground) {
        try {
            $taskLoaded=@(([Diagnostics.Process]::GetProcessById($taskPrior.ProcessId)).Modules | Where-Object { $_.FileName.Replace('\','/').StartsWith($taskProject+'/',[StringComparison]::OrdinalIgnoreCase) })
            if($taskLoaded.Count -eq 0) { Write-Output "Project DLLs not loaded by PID $($taskPrior.ProcessId); preserving its startup"; continue }
        } catch [ArgumentException] { continue }
        Write-Output "Waiting for project commandlet PID $($taskPrior.ProcessId)"
        try {[Diagnostics.Process]::GetProcessById($taskPrior.ProcessId).WaitForExit()} catch [ArgumentException] {}
    }
    $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject") } | Where-Object {
        if($_.Name -eq 'UnrealEditor.exe') { $true }
        else {
            try { @(([Diagnostics.Process]::GetProcessById($_.ProcessId)).Modules | Where-Object {$_.FileName.Replace('\','/').StartsWith($taskProject+'/',[StringComparison]::OrdinalIgnoreCase)}).Count -gt 0 }
            catch [ArgumentException] { $false }
        }
    })
    if($taskTarget -eq 'FPSGAMEEditor' -and $taskEditors.Count -gt 0){throw 'Project editor binaries occupied; sources preserved'}
    $taskLog=Join-Path $taskOutput "build-$taskTarget.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> (Join-Path $taskOutput "build-$taskTarget-stdout.log")
    $taskCode=$LASTEXITCODE
    $taskResults+=@{target=$taskTarget;exit_code=$taskCode;log=$taskLog;completed_utc=[DateTime]::UtcNow.ToString('o')}
    [IO.File]::WriteAllText((Join-Path $taskOutput 'build.json'),(@{results=$taskResults;runtime_tested=$false;tests_run=$false}|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
    Write-Output "$taskTarget exit=$taskCode"
    if($taskCode -ne 0){Get-Content -LiteralPath (Join-Path $taskOutput "build-$taskTarget-stdout.log") -Tail 18; throw "Build failed: $taskTarget"}
}
