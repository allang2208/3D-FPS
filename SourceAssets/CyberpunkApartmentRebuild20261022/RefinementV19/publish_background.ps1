param([int]$BuildProcessId=0,[int]$MaximumWaitSeconds=7200,[string]$RunName='publish-01',[string]$ScriptName='publish.py',[switch]$MaterialCompilation)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskProjectPattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$taskOutput=Join-Path $taskRoot 'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV19'
if($BuildProcessId -gt 0 -and (Get-Process -Id $BuildProcessId -ErrorAction SilentlyContinue)){Wait-Process -Id $BuildProcessId}
$taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    Write-Output 'Waiting once in the existing UE publication mutex queue.'
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds($MaximumWaitSeconds))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'Existing UE batch retained; publication remains pending.'}
    while($true) {
        if([DateTime]::UtcNow -gt $taskDeadline){throw 'Existing project batch retained; publish not started.'}
        $taskProcesses=@(Get-CimInstance Win32_Process)
        if($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match $taskProjectPattern}){throw 'Preserving the open editor; publish through its existing bridge.'}
        $taskOwners=@($taskProcesses | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match $taskProjectPattern)})
        if(-not $taskOwners.Count){break}
        Start-Sleep -Seconds 8
    }
    $taskRenderFlag=if($MaterialCompilation){'-AllowCommandletRendering'}else{'-nullrhi'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskOutput/$ScriptName" -unattended -nosplash -nosound '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' $taskRenderFlag "-abslog=$taskOutput/$RunName.log" *> "$taskOutput/$RunName-console.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;game_run=$false;editor_opened=$false;log="$taskOutput/$RunName.log"} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/$RunName.json" -Encoding utf8
    if($taskExit -ne 0){throw 'Apartment asset/map publishing failed; see saved commandlet log.'}
    Write-Output 'Apartment production batch completed.'
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
