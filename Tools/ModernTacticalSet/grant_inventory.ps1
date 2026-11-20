# Use the existing native, journaled grant commandlet on an isolated copy.
# Publish the completed five-item profile only after all five insertions succeed.
$ErrorActionPreference='Stop'
$tacticalProject='D:/FPS3D/FPSGAME'
$tacticalRoot=Join-Path $tacticalProject 'SourceAssets/ModernTacticalSet20261113/Integration'
$tacticalSource=Join-Path $tacticalProject 'Saved/SaveGames'
$tacticalHost=Join-Path $tacticalRoot 'GrantHost'
$tacticalReceipt=Join-Path $tacticalRoot 'inventory_grant.json'
if(Test-Path -LiteralPath $tacticalReceipt){
    $old=Get-Content -LiteralPath $tacticalReceipt -Raw | ConvertFrom-Json
    if($old.completed){Write-Output 'TS01 saved inventory grant is already complete.';exit 0}
}
$tacticalPublished=Get-Content -LiteralPath (Join-Path $tacticalRoot 'published.json') -Raw | ConvertFrom-Json
if(-not $tacticalPublished.completed){throw 'Save and publish the complete set first'}
$tacticalGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$tacticalHeld=$false
try{
    try{$tacticalHeld=$tacticalGate.WaitOne()}catch [Threading.AbandonedMutexException]{$tacticalHeld=$true}
    $tacticalLive=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','FPSGAME.exe','FPSGAME-Win64-Shipping.exe') -and $_.CommandLine -like '*FPSGAME*' })
    if($tacticalLive.Count){throw 'The live game/editor owns its inventory. Keep the prepared grant copy until it is closed.'}
    [void](New-Item -ItemType Directory -Path "$tacticalHost/Saved/SaveGames" -Force)
    foreach($part in @('Binaries','Config','Intermediate')){
        if(-not(Test-Path -LiteralPath "$tacticalHost/$part")){[void](New-Item -ItemType Junction -Path "$tacticalHost/$part" -Target "$tacticalRoot/AssetHost/$part")}
    }
    foreach($part in @('Content','Plugins')){
        if(-not(Test-Path -LiteralPath "$tacticalHost/$part")){[void](New-Item -ItemType Junction -Path "$tacticalHost/$part" -Target "$tacticalProject/$part")}
    }
    Copy-Item -LiteralPath "$tacticalRoot/AssetHost/FPSGAME.uproject" -Destination "$tacticalHost/FPSGAME.uproject" -Force
    $tacticalStateFile=Join-Path $tacticalRoot 'grant-prepared.json'
    if(-not(Test-Path -LiteralPath $tacticalStateFile)){
        $tacticalInputs=@();$tacticalBackup=Join-Path $tacticalRoot 'BeforeGrant';[void](New-Item -ItemType Directory -Path $tacticalBackup -Force)
        foreach($suffix in @('_A','_B')){foreach($ext in @('.sav','.sha1')){
            $name='ColdSteelPlayer_PIE_0'+$suffix+$ext;$file=Join-Path $tacticalSource $name
            if(-not(Test-Path -LiteralPath $file)){continue}
            Copy-Item -LiteralPath $file -Destination (Join-Path $tacticalBackup $name)
            Copy-Item -LiteralPath $file -Destination "$tacticalHost/Saved/SaveGames/ColdSteelPlayer$suffix$ext"
            $tacticalInputs+=@{name=$name;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash}
        }}
        if(-not $tacticalInputs.Count){throw 'The current PIE player has no persisted inventory'}
        $tacticalGrants=@('ue_modern_kevlar_vest','ue_modern_tactical_helmet','ue_modern_tactical_gloves','ue_modern_tactical_pants','ue_modern_tactical_boots') | ForEach-Object { @{definition=$_;instance_id=([guid]::NewGuid().ToString('N'))} }
        @{source_slot='ColdSteelPlayer_PIE_0';inputs=$tacticalInputs;grants=$tacticalGrants;steps=@();backup=$tacticalBackup} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tacticalStateFile -Encoding utf8NoBOM
    }
    $tacticalState=Get-Content -LiteralPath $tacticalStateFile -Raw | ConvertFrom-Json
    foreach($inputFile in $tacticalState.inputs){if((Get-FileHash -LiteralPath (Join-Path $tacticalSource $inputFile.name) -Algorithm SHA256).Hash -ne $inputFile.sha256){throw 'Player inventory changed during preparation. Preserve both versions; do not overwrite.'}}
    foreach($grant in $tacticalState.grants){
        if(@($tacticalState.steps | Where-Object {$_.instance_id -eq $grant.instance_id}).Count){continue}
        $tacticalLog=Join-Path $tacticalRoot ('Logs/grant-'+$grant.definition+'-'+(Get-Date -Format 'HHmmss')+'.log')
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$tacticalHost/FPSGAME.uproject" '/Engine/Maps/Entry' '-run=GrantPlayerAKM' ('-Item='+$grant.definition) ('-GrantId='+$grant.instance_id) '-Magazine=0' '-Reserve=0' '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-Multiprocess' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen' '-AssetGatherAll=false' '-asyncskinnedassetcompilation=0' '-asyncstaticmeshcompilation=0' '-asynctexturecompilation=0' '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' ('-abslog='+$tacticalLog) *> ($tacticalLog+'.txt')
        if($LASTEXITCODE -ne 0){Get-Content -LiteralPath ($tacticalLog+'.txt') -Tail 12;throw ('Native grant stopped: '+$grant.definition)}
        $tacticalLines=Get-Content -LiteralPath $tacticalLog
        $tacticalAdded=@($tacticalLines | Select-String 'PLAYER_ITEM_GRANT: SAVED.*slot=(ColdSteelPlayer_[AB]) row=(\d+) column=(\d+)')
        if(-not $tacticalAdded.Count){throw 'Native grant did not provide its saved inventory position; retain the isolated profile.'}
        $m=$tacticalAdded[-1].Matches[0]
        $tacticalState.steps+=@{definition=$grant.definition;instance_id=$grant.instance_id;shadow_slot=$m.Groups[1].Value;row=[int]$m.Groups[2].Value;column=[int]$m.Groups[3].Value;log=$tacticalLog}
        $tacticalState | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tacticalStateFile -Encoding utf8NoBOM
        Write-Output ('TS01_SHADOW_ITEM_SAVED '+$grant.definition)
    }
    foreach($inputFile in $tacticalState.inputs){if((Get-FileHash -LiteralPath (Join-Path $tacticalSource $inputFile.name) -Algorithm SHA256).Hash -ne $inputFile.sha256){throw 'The live inventory changed. Keep the completed shadow set without overwriting it.'}}
    $tacticalShadow=$tacticalState.steps[-1].shadow_slot;$tacticalTarget=$tacticalShadow.Replace('ColdSteelPlayer_','ColdSteelPlayer_PIE_0_')
    foreach($ext in @('.sav','.sha1')){
        $dest=Join-Path $tacticalSource ($tacticalTarget+$ext);$temp=$dest+'.ts01.tmp'
        Copy-Item -LiteralPath "$tacticalHost/Saved/SaveGames/$tacticalShadow$ext" -Destination $temp
        [IO.File]::Move($temp,$dest,$true)
    }
    @{completed=$true;source_slot=$tacticalState.source_slot;target_slot=$tacticalTarget;granted=$tacticalState.steps;backup=$tacticalState.backup;runtime_tested=$false;method='existing native GrantPlayerAKM commandlet, isolated complete-set transaction'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tacticalReceipt -Encoding utf8NoBOM
    Write-Output ('TS01_BACKPACK_SET_SAVED '+$tacticalTarget+'; five items')
}finally{if($tacticalHeld){$tacticalGate.ReleaseMutex()};$tacticalGate.Dispose()}
