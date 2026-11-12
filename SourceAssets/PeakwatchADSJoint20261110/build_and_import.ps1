$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$deadline=(Get-Date).AddMinutes(15)
try {
    while(-not $held){
        try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(30))}
        catch [Threading.AbandonedMutexException] {$held=$true}
        if((Get-Date) -gt $deadline){throw 'UE batch remains occupied; no processes stopped.'}
    }
    $announced=$false
    while($true){
        $jobs=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $jobs.Count){break}
        if(-not $announced){Write-Output 'Waiting for existing build/asset process; preserving it.';$announced=$true}
        if((Get-Date) -gt $deadline){throw 'Existing build/asset job retained; batch deferred.'}
        Start-Sleep -Seconds 10
    }
    & "$project/Tools/Build/Build-Editor.ps1"
    if($LASTEXITCODE -ne 0){throw 'Editor build did not finish'}
    $buildLog=Get-ChildItem -LiteralPath "$project/Saved/BuildEditor" -Filter 'build-*.log' |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    [ordered]@{result='Succeeded';log=$buildLog.FullName;runtime_tested=$false} |
        ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/native-build.json" -Encoding utf8
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if($editors.Count){throw 'Editor appeared before asset step; no concurrent import started.'}
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $log="$PSScriptRoot/import-$stamp.log";$out="$PSScriptRoot/import-$stamp.stdout.txt"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" `
        -run=pythonscript "-script=$PSScriptRoot/import_joint.py" -nullrhi -unattended -nop4 -nosound -nosplash `
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$log" *> $out
    $code=$LASTEXITCODE
    [ordered]@{exit_code=$code;log=$log;stdout=$out;runtime_tested=$false} |
        ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/import-result.json" -Encoding utf8
    if($code -ne 0){throw "Import exited $code; see $log"}
    & python "$PSScriptRoot/publish_catalog.py"
    if($LASTEXITCODE -ne 0){throw 'Catalog publication failed; saved asset retained'}
    Write-Output 'Peakwatch joint and ADS production integration completed; gameplay remains manual.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
