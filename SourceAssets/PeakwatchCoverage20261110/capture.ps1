param([string]$Label='production')
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$output="$PSScriptRoot/Review/$Label-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Path $output -Force | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    while(-not $held){
        try{$held=$gate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$held=$true}
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing UE batch retained; capture not started'}
    }
    $existing=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($existing.Count){throw 'Existing engine/build process retained; capture not started'}
    $profile='PeakwatchCoverageAudit_'+(Get-Date -Format 'yyyyMMddHHmmss')
    $captureArgs=@(('"'+$project+'/FPSGAME.uproject"'),'/Game/GameMaps/DayNight_Lighting','-game','-RenderOffscreen',
        '-windowed','-ResX=1600','-ResY=900','-ForceRes','-unattended','-nosplash','-nosound','-NoSteam','-SkipStartupMenu',
        '-PeakwatchCoverageAudit',('-ColdSteelProfile='+$profile),('-PeakwatchCoverageOutput="'+$output+'"'),
        ('-UserDir="'+$output+'/User/"'),('-abslog="'+$output+'/runtime.log"'),'-ExecCmds="t.MaxFPS 60"')
    $process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $captureArgs -WindowStyle Hidden -PassThru
    [ordered]@{pid=$process.Id;output=$output;profile=$profile;arguments=$captureArgs;dll_sha256=(Get-FileHash "$project/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$output/launch.json" -Encoding utf8
    Write-Output "PEAKWATCH_REVIEW_STARTED pid=$($process.Id) output=$output"
    $deadline=[DateTime]::UtcNow.AddMinutes(12)
    while(-not $process.WaitForExit(1000)){
        if([DateTime]::UtcNow -gt $deadline){$process.Kill();throw 'Owned offscreen review exceeded its deadline'}
    }
    $process.Refresh()
    [ordered]@{exit_code=$process.ExitCode;output=$output} | ConvertTo-Json | Set-Content -LiteralPath "$output/process-result.json" -Encoding utf8
    if($process.ExitCode -ne 0){throw "Review process exited $($process.ExitCode); see $output/runtime.log"}
    Write-Output "PEAKWATCH_REVIEW_FINISHED $output"
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
