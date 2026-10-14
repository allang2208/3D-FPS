param(
    [string[]]$Targets=@('FPSGAME','FPSGAMEEditor'),
    [string]$EngineRoot='E:/Program Files (x86)/UE_5.8',
    [string]$OutputSubdirectory='Dealer20261004'
)
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskOutput=Join-Path $taskProject ('Saved/'+$OutputSubdirectory)
[IO.Directory]::CreateDirectory($taskOutput)|Out-Null
$taskReceipt=Join-Path $taskOutput 'delivery.json'
$taskState=if(Test-Path -LiteralPath $taskReceipt){Get-Content -LiteralPath $taskReceipt -Raw|ConvertFrom-Json -AsHashtable}else{@{gameBuild='pending';editorBuild='pending';gameplayTested=$false}}
function Save-State {[IO.File]::WriteAllText($taskReceipt,($taskState|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))}
foreach($taskTarget in $Targets){
    $taskNotified=$false
    while(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealBuildTool|cl|link|UnrealEditor-Cmd)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }){
        if(-not $taskNotified){Write-Output 'Waiting for the current native build or asset commandlet.';$taskNotified=$true}
        Start-Sleep -Seconds 10
    }
    $taskKey=if($taskTarget -eq 'FPSGAME'){'gameBuild'}else{'editorBuild'}
    if($taskTarget -eq 'FPSGAMEEditor'){
        $taskDLL=Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        if(Test-Path -LiteralPath $taskDLL){
            try{$taskFile=[IO.File]::Open($taskDLL,'Open','ReadWrite','None');$taskFile.Dispose()}
            catch{$taskState[$taskKey]='blocked-dll-in-use';Save-State;throw 'Preserve the editor currently holding the DLL.'}
        }
    }
    $taskState[$taskKey]='building';Save-State
    Write-Output "Building $taskTarget in the background."
    & "$EngineRoot/Engine/Build/BatchFiles/Build.bat" $taskTarget Win64 Development "-Project=$taskProject/FPSGAME.uproject" `
        -NoHotReload -NoHotReloadFromIDE "-Log=$taskOutput/$taskKey.log" *> "$taskOutput/$taskKey-output.log"
    $taskState[$taskKey]=if($LASTEXITCODE -eq 0){'succeeded'}else{'failed'};Save-State
    if($LASTEXITCODE -ne 0){throw "Native build failed: $taskOutput/$taskKey-output.log"}
    Write-Output "$taskTarget build saved."
}
