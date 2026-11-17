param([string]$Runtime='D:/FPS3D/FPSGAME/Saved/MapMarkerSharing20261115/normal-01/Runtime',[string]$Run='lifecycle-01')
$ErrorActionPreference='Stop'
$mlRoot='D:/FPS3D/FPSGAME';$mlOut="$mlRoot/Saved/MapMarkerSharing20261115/$Run"
$mlGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$mlHeld=$false;$mlPeer=$null
if(-not(Test-Path "$Runtime/Binaries/Win64/UnrealEditor-FPSGAME.dll")){throw 'A fixed runtime from the network check is required'}
if(Test-Path "$mlOut/receipt.json"){throw 'Use a new run name'}
New-Item -ItemType Directory -Force -Path $mlOut | Out-Null
try{
 try{$mlHeld=$mlGate.WaitOne(0)}catch [Threading.AbandonedMutexException]{$mlHeld=$true}
 while(-not $mlHeld){try{$mlHeld=$mlGate.WaitOne(50000)}catch [Threading.AbandonedMutexException]{$mlHeld=$true}}
 $mlArgs=@("`"$Runtime/FPSGAME.uproject`"",'-run=ColdSteelDungeonFogCheck','-NetworkLifecycle','-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
 '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
 '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh',
 "-UserDir=`"$mlOut/Profile/`"","-ColdSteelProfile=MapMarker_$Run","-abslog=`"$mlOut/check.log`"")
 $mlPeer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $mlArgs -WorkingDirectory $mlRoot -WindowStyle Hidden -PassThru
 $null=$mlPeer.Handle
 @{pid=$mlPeer.Id;args=$mlArgs;dll=(Get-FileHash "$Runtime/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Algorithm SHA256).Hash;started=(Get-Date).ToString('o')} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$mlOut/launch.json" -Encoding utf8
 $mlUntil=[DateTime]::UtcNow.AddMinutes(10)
 while(-not $mlPeer.WaitForExit(5000)){if([DateTime]::UtcNow -gt $mlUntil){throw 'Commandlet timed out'}}
 $mlLine=Select-String -LiteralPath "$mlOut/check.log" -Pattern 'DungeonFogLifecycle: (\d+) checks, (\d+) failures' | Select-Object -Last 1
 $mlOK=$mlPeer.ExitCode -eq 0 -and $mlLine -and $mlLine.Matches[0].Groups[2].Value -eq '0'
 @{passed=[bool]$mlOK;exit_code=$mlPeer.ExitCode;summary=$mlLine.Line;scope='simulated dungeon lifecycle, no UDP and no rendered acceptance';completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$mlOut/receipt.json" -Encoding utf8
 if(-not $mlOK){throw 'Lifecycle check failed; see log and receipt'}
 Write-Output $mlLine.Line
}finally{
 if($mlPeer){$mlPeer.Refresh();if(-not $mlPeer.HasExited){$mlCurrent=Get-CimInstance Win32_Process -Filter "ProcessId=$($mlPeer.Id)";if($mlCurrent.CommandLine -like "*$mlOut*" -and $mlCurrent.CommandLine -like '*-NetworkLifecycle*'){Stop-Process -Id $mlPeer.Id}}}
 if($mlHeld){$mlGate.ReleaseMutex()};$mlGate.Dispose()
}
