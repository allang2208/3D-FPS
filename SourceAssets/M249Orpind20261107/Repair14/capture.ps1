param([string]$Label='before',[string]$Equipment='')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$output="$PSScriptRoot/$Label-$stamp"
New-Item -ItemType Directory -Path $output | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(!$held){throw 'Existing UE batch retained'}
    $existing=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
    if($existing.Count){throw 'Existing project process retained; capture not started'}
    $captureArgs=@(('"'+$project+'/FPSGAME.uproject"'),'/Game/GameMaps/DayNight_Lighting','-game','-RenderOffscreen','-windowed','-ResX=1600','-ResY=900','-ForceRes','-unattended','-nosplash','-nosound','-NoSteam','-SkipStartupMenu','-ScopeScreenshotAudit','-M249OpticObstruction',('-ColdSteelProfile=ScopeScreenshotAudit_M249_'+$stamp),('-ScopeScreenshotOutput="'+$output+'"'),('-UserDir="'+$output+'/User/"'),('-abslog="'+$output+'/runtime.log"'))
    if($Equipment){$captureArgs+=('-M249OpticEquipment="'+$Equipment+'"')}
    $process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $captureArgs -WindowStyle Hidden -PassThru
    @{pid=$process.Id;output=$output;profile='ScopeScreenshotAudit_M249_'+$stamp;started=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/active_capture.json" -Encoding utf8
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    while(!$process.WaitForExit(1000)){
        if([DateTime]::UtcNow -gt $deadline){$process.Kill();throw 'Owned offscreen capture timed out'}
    }
    if($process.ExitCode -ne 0){throw "Owned capture exit $($process.ExitCode): $output"}
    Write-Output "M249_ADS_CAPTURE_SAVED $output"
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
