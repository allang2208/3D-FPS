param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskProjectFile=Join-Path $taskProject 'FPSGAME.uproject'
$taskOutput=Join-Path $taskProject 'Saved/BigBlind'
[IO.Directory]::CreateDirectory($taskOutput)|Out-Null
$taskState=[ordered]@{assetsSaved=$false;gameBuild='pending';editorBuild='pending';gameplayTested=$false;rendered=$false}
function Save-State {
    [IO.File]::WriteAllText((Join-Path $taskOutput 'delivery.json'),($taskState|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
function Project-Editors {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        ($_.CommandLine -replace '\\','/') -match [regex]::Escape(($taskProjectFile -replace '\\','/'))
    })
}
function Wait-BuildWindow {
    $taskAnnounced=$false
    do {
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -in @('cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        $taskCmd=@(Project-Editors | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' })
        if($taskBusy.Count -or $taskCmd.Count){
            if(!$taskAnnounced){Write-Host 'BIG_BLIND Waiting for current build/asset processes to finish.';$taskAnnounced=$true}
            Start-Sleep -Seconds 10
        }
    }while($taskBusy.Count -or $taskCmd.Count)
}
Save-State
Wait-BuildWindow
$taskAuthor=Join-Path $PSScriptRoot 'build_big_blind_glow.py'
if(@(Project-Editors | Where-Object { $_.Name -eq 'UnrealEditor.exe' }).Count){
    & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskAuthor -OutputFile (Join-Path $taskOutput 'asset-bridge.txt') -MaxOutputChars 3000
    if($LASTEXITCODE -ne 0){throw 'Big Blind asset bridge failed; preserve existing packages.'}
}else{
    & (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') $taskProjectFile -run=pythonscript "-script=$taskAuthor" -unattended -nop4 -nosplash -NullRHI -nosound -Multiprocess -DDC=InstalledNoZenLocalFallback "-abslog=$(Join-Path $taskOutput 'asset-commandlet.log')" *> (Join-Path $taskOutput 'asset-commandlet-output.log')
    if($LASTEXITCODE -ne 0){throw 'Big Blind asset commandlet failed; preserve saved packages.'}
}
if(!(Test-Path -LiteralPath (Join-Path $taskOutput 'authored.json'))){throw 'Material authoring did not report a saved asset.'}
$taskState.assetsSaved=$true;Save-State
Write-Host 'BIG_BLIND Material saved.'
$taskBuild=Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat'
foreach($taskTarget in @('FPSGAME','FPSGAMEEditor')){
    Wait-BuildWindow
    $taskKey=if($taskTarget -eq 'FPSGAME'){'gameBuild'}else{'editorBuild'}
    if($taskTarget -eq 'FPSGAMEEditor'){
        $taskDLL=Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        if(Test-Path -LiteralPath $taskDLL){
            try{$taskFile=[IO.File]::Open($taskDLL,'Open','ReadWrite','None');$taskFile.Dispose()}
            catch{$taskState[$taskKey]='blocked-dll-in-use';Save-State;throw 'Editor DLL is in use. Preserve the running editor; do not close or restart it.'}
        }
    }
    Write-Host "BIG_BLIND Building $taskTarget."
    & $taskBuild $taskTarget Win64 Development "-Project=$taskProjectFile" -NoHotReload -NoHotReloadFromIDE "-Log=$(Join-Path $taskOutput ($taskKey+'.log'))"
    if($LASTEXITCODE -ne 0){
        $taskState[$taskKey]='failed'
        if($taskKey -eq 'gameBuild'){$taskState.editorBuild='blocked-by-game-compile-errors'}
        Save-State;throw "$taskTarget build failed. See Saved/BigBlind/$taskKey.log."
    }
    $taskState[$taskKey]='succeeded';Save-State
}
Write-Host 'BIG_BLIND Background authoring and builds complete. No editor, game or tests launched.'
