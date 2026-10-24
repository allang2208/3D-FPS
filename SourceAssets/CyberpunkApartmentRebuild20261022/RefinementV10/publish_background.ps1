param([int]$BuildProcessId=0,[int]$MaximumWaitSeconds=7200,[string]$RunName='publish-01',[string]$ScriptName='publish.py',[switch]$MaterialCompilation)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskProjectPattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$taskOutput=Join-Path $taskRoot 'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV10'
if($BuildProcessId -gt 0 -and (Get-Process -Id $BuildProcessId -ErrorAction SilentlyContinue)){Wait-Process -Id $BuildProcessId}
$taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    while($true) {
        if([DateTime]::UtcNow -gt $taskDeadline){throw 'Existing project batch retained; publish not started.'}
        $taskProcesses=@(Get-CimInstance Win32_Process)
        if($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match $taskProjectPattern}){throw 'Preserving the open editor; publish through its existing bridge.'}
        $taskOwners=@($taskProcesses | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match $taskProjectPattern)})
        if($taskOwners.Count){Start-Sleep -Seconds 8;continue}
        try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(8))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
        if(-not $taskHeld){continue}
        $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match $taskProjectPattern) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
        if(-not $taskOwners.Count){break}
        $taskGate.ReleaseMutex();$taskHeld=$false
        Start-Sleep -Seconds 8
    }
    $taskRenderFlag=if($MaterialCompilation){'-AllowCommandletRendering'}else{'-nullrhi'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskOutput/$ScriptName" -unattended -nosplash -nosound $taskRenderFlag "-abslog=$taskOutput/$RunName.log" *> "$taskOutput/$RunName-console.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;game_run=$false;editor_opened=$false;log="$taskOutput/$RunName.log"} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/$RunName.json" -Encoding utf8
    if($taskExit -ne 0){throw 'Apartment asset/map publishing failed; see saved commandlet log.'}
    Write-Output 'Apartment assets and map saved.'
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
