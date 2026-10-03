param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8',[string]$OutputSubdirectory='BoundlessStrength')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskProjectFile=Join-Path $taskProject 'FPSGAME.uproject'
$taskOutput=Join-Path $taskProject ('Saved/'+$OutputSubdirectory)
[IO.Directory]::CreateDirectory($taskOutput)|Out-Null
$taskState=[ordered]@{gameBuild='pending';editorBuild='pending';gameplayTested=$false}
function Save-State {
    [IO.File]::WriteAllText((Join-Path $taskOutput 'delivery.json'),($taskState|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
function Wait-BuildWindow {
    $taskAnnounced=$false
    do {
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -in @('cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject')
        })
        if($taskBusy.Count){
            if(!$taskAnnounced){Write-Host 'BOUNDLESS_STRENGTH Waiting for current build/asset processes to finish.';$taskAnnounced=$true}
            Start-Sleep -Seconds 10
        }
    }while($taskBusy.Count)
}
Save-State
foreach($taskTarget in @('FPSGAME','FPSGAMEEditor')){
    Wait-BuildWindow
    $taskKey=if($taskTarget -eq 'FPSGAME'){'gameBuild'}else{'editorBuild'}
    if($taskTarget -eq 'FPSGAMEEditor'){
        $taskDLL=Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        if(Test-Path -LiteralPath $taskDLL){
            try{$taskFile=[IO.File]::Open($taskDLL,'Open','ReadWrite','None');$taskFile.Dispose()}
            catch{$taskState[$taskKey]='blocked-dll-in-use';Save-State;throw 'Editor DLL is in use. Preserve the running editor.'}
        }
    }
    Write-Host "BOUNDLESS_STRENGTH Building $taskTarget."
    & (Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat') $taskTarget Win64 Development "-Project=$taskProjectFile" -NoHotReload -NoHotReloadFromIDE "-Log=$(Join-Path $taskOutput ($taskKey+'.log'))" *> (Join-Path $taskOutput ($taskKey+'-output.log'))
    if($LASTEXITCODE -ne 0){
        $taskState[$taskKey]='failed'
        if($taskKey -eq 'gameBuild'){$taskState.editorBuild='blocked-by-game-compile-errors'}
        Save-State;throw "$taskTarget build failed. See $taskOutput/$taskKey.log."
    }
    $taskState[$taskKey]='succeeded';Save-State
    Write-Host "BOUNDLESS_STRENGTH $taskTarget build succeeded."
}
Write-Host 'BOUNDLESS_STRENGTH Background builds complete. No editor, game or tests launched.'
