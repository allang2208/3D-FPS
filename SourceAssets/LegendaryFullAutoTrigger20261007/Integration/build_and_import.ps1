$ErrorActionPreference='Stop'
$triggerProject='D:/FPS3D/FPSGAME'
$triggerOutput=$PSScriptRoot
$triggerBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$triggerReceipt=@{runtime_tested=$false;targets=@{};texture_saved=$false}
function Wait-TriggerBuildSlot {
    $triggerNotified=$false
    while($true){
        $triggerBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealBuildTool.exe' -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $triggerBusy.Count){return}
        if(-not $triggerNotified){Write-Output 'Waiting for the current native build to finish.';$triggerNotified=$true}
        Start-Sleep -Seconds 20
    }
}
function Assert-TriggerEditorClosed {
    $triggerEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='FPSGAME.exe'" | Where-Object {
        $_.Name -eq 'FPSGAME.exe' -or [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($triggerEditors.Count){throw 'The project is running. No editor or game process was stopped.'}
}
foreach($triggerTarget in @('FPSGAMEEditor','FPSGAME')){
    Wait-TriggerBuildSlot
    Assert-TriggerEditorClosed
    $triggerLog=Join-Path $triggerOutput ("build-$triggerTarget-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output "Building $triggerTarget"
    & $triggerBuild $triggerTarget Win64 Development "-Project=$triggerProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$triggerLog" *> ($triggerLog+'.console.txt')
    $triggerCode=$LASTEXITCODE
    $triggerReceipt.targets[$triggerTarget]=@{exit_code=$triggerCode;log=$triggerLog}
    $triggerReceipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $triggerOutput 'build_receipt.json') -Encoding UTF8
    Get-Content -LiteralPath $triggerLog -Tail 12
    if($triggerCode -ne 0){throw "Native build failed: $triggerLog"}
}
Wait-TriggerBuildSlot
$triggerGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$triggerHeld=$false
try {
    while(-not $triggerHeld){
        try{$triggerHeld=$triggerGate.WaitOne(15000)}catch [Threading.AbandonedMutexException]{$triggerHeld=$true}
    }
    Assert-TriggerEditorClosed
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$triggerProject/FPSGAME.uproject" -run=pythonscript "-script=$triggerOutput/import_icon.py" `
        -unattended -nop4 -nosplash -nosound -NullRHI `
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
        "-abslog=$triggerOutput/import-commandlet.log" *> "$triggerOutput/import-console.log"
    if($LASTEXITCODE -ne 0){throw "Icon import failed ($LASTEXITCODE)."}
    if(-not (Test-Path -LiteralPath (Join-Path $triggerOutput 'import_receipt.json'))){throw 'Icon import did not return a save receipt.'}
    $triggerReceipt.texture_saved=$true
    $triggerReceipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $triggerOutput 'build_receipt.json') -Encoding UTF8
    Write-Output 'FULL_AUTO_TRIGGER_BUILD_AND_IMPORT_COMPLETE'
} finally {
    if($triggerHeld){$triggerGate.ReleaseMutex()}
    $triggerGate.Dispose()
}
