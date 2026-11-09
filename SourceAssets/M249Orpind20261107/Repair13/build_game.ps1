$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Build batch wait expired'}
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
        if($busy.Count){if([DateTime]::UtcNow -gt $deadline){throw 'Existing build retained'};Start-Sleep -Seconds 5}
    }while($busy.Count)
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $log="$project/Saved/Logs/M249Repair13GameBuild.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$project/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=6 "-Log=$log" *> "$log.console"
    $code=$LASTEXITCODE
    @{exit_code=$code;target='FPSGAME';log=$log;runtime_tested=$false;editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_game_receipt.json" -Encoding utf8
    Get-Content -LiteralPath "$log.console" -Tail 12
    if($code -ne 0){throw "M249 Game build exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
