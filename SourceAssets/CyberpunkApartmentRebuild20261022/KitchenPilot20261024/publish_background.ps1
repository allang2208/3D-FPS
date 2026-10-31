param([string]$ScriptName='inspect_ue.py',[string]$RunName='ue-scope',[int]$MaximumWaitSeconds=3600)
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$out=Join-Path $root 'SourceAssets/CyberpunkApartmentRebuild20261022/KitchenPilot20261024'
$pattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$deadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$mutex.WaitOne([TimeSpan]::FromSeconds($MaximumWaitSeconds))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch mutex retained; no asset changes were submitted.'}
    while($true){
        if([DateTime]::UtcNow -gt $deadline){throw 'UE ownership retained; no asset changes were submitted.'}
        $processes=@(Get-CimInstance Win32_Process)
        if($processes|Where-Object{$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match $pattern}){throw 'The production project is open. Use the existing MCP editor instead of a second process.'}
        $free=(Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='D:'").FreeSpace
        if($free -lt 300MB){throw "Insufficient project-volume headroom: $free bytes; no commandlet or map write submitted."}
        $owners=@($processes|Where-Object{($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match $pattern)})
        if(-not $owners.Count){break}
        Start-Sleep -Seconds 8
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$root/FPSGAME.uproject" -run=pythonscript "-script=$out/$ScriptName" -unattended -nosplash -nosound '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' -nullrhi "-abslog=$out/$RunName.log" *> "$out/$RunName-console.log"
    $code=$LASTEXITCODE
    @{exit_code=$code;game_run=$false;editor_opened=$false;log="$out/$RunName.log"}|ConvertTo-Json|Set-Content -LiteralPath "$out/$RunName.json" -Encoding utf8
    if($code -ne 0){throw 'UE background batch failed; inspect its saved log.'}
    Write-Output "Kitchen background batch completed: $RunName"
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
