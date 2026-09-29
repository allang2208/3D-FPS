$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$projectRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot '../../..'))
$processes = @(Get-CimInstance Win32_Process)
if (@($processes | Where-Object {
    ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
    $_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
}).Count) { throw 'UE or a native build is active; no build submitted and no process stopped.' }
$log = Join-Path $taskRoot 'build-native.log'
$project = Join-Path $projectRoot 'FPSGAME.uproject'
# Ordinary dependency-aware build: do not use NoUBTMakefiles after header changes.
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$project" '-NoHotReload' '-NoHotReloadFromIDE' "-Log=$log" *> (Join-Path $taskRoot 'build-console.log')
$result = [ordered]@{ exit_code=$LASTEXITCODE; log=$log; finished_utc=[DateTime]::UtcNow.ToString('o'); target='FPSGAMEEditor Win64 Development'; runtime_tested=$false }
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'build-result.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $taskRoot 'build-console.log') -Tail 16
if ($LASTEXITCODE -ne 0) { throw "Native build failed; see $log" }
