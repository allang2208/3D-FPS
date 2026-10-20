param([int]$Sleep = 0)
if ($Sleep) { Start-Sleep -Seconds $Sleep }
Set-Location $PSScriptRoot
$a = foreach ($b in 'batch1','batch2','batch3','batch4') { "$b=" + (python left_rawfix.py $b) }
"$(Get-Date -Format HH:mm) anim left: $($a -join ' ')  failed: $((Get-ChildItem InstalledRaw -Filter *.failed.json).Count)"
foreach ($b in 'batch1','batch2','batch3','batch4') {
    $p = @(Get-ChildItem "Work\$b" -Filter *.json -ErrorAction SilentlyContinue | Where-Object { $_.BaseName -match '^[0-9a-f]{12}$' })
    $i = @($p | Where-Object { Test-Path "Installed\$($_.BaseName).json" }).Count
    $f = @($p | Where-Object { Test-Path "Installed\$($_.BaseName).failed.json" }).Count
    $pp = @(Get-ChildItem "Work\$($b)_pose" -Filter *.json -ErrorAction SilentlyContinue | Where-Object { $_.BaseName -match '^[0-9a-f]{12}$' })
    $pi = @($pp | Where-Object { Test-Path "Installed_pose\$($_.BaseName).json" }).Count
    "  $b meshes $i/$($p.Count) (failed $f)  pose payloads $($pp.Count) installed $pi"
}
$u = Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'UnrealEditor.exe','UnrealEditor-Cmd.exe','dotnet.exe' } | ForEach-Object { $_.Name + ':' + ([regex]::Match($_.CommandLine, '(-script=\S+|FPSGAME\w* Win64)').Value -replace '.*\\','') }
"  procs: $($u -join ', ')  freeGB: $([math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1))"
