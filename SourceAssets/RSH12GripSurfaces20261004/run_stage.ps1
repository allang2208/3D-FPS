param([Parameter(Mandatory=$true)][ValidateSet('Import','Build')][string]$Stage)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject 'SourceAssets/RSH12GripSurfaces20261004'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    Write-Output "RSH grip surface $Stage owns the shared authoring window."
    while ($true) {
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
        if ($taskEditors | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {throw 'FPSGAME editor is open; no editor was stopped.'}
        $taskBuilders=@(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if ($taskEditors.Count -eq 0 -and ($Stage -ne 'Build' -or $taskBuilders.Count -eq 0)) {break}
        Start-Sleep -Seconds 15
    }
    if ($Stage -eq 'Build') {
        $taskLog=Join-Path $taskProject 'Saved/BuildEditor/rsh12-grip-surfaces-20261004.log'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -Module=FPSGAME -MaxParallelActions=4 "-Log=$taskLog"
        if ($LASTEXITCODE -ne 0) {throw "RSH grip surface build failed ($LASTEXITCODE)."}
        $taskDll=Get-Item -LiteralPath (Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
        @{status='Succeeded';log=$taskLog;dll=$taskDll.FullName;dllSavedAtUtc=$taskDll.LastWriteTimeUtc.ToString('o');runtimeTested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'build_receipt.json') -Encoding utf8
    } else {
        $taskScript=if($Stage -eq 'Icon'){'import_icon.py'}else{'import_assets.py'}
        & "$taskProject/Tools/ModularOutfit/Run-Authoring.ps1" -Script "SourceAssets/RSH12GripSurfaces20261004/$taskScript" -Log "SourceAssets/RSH12GripSurfaces20261004/$Stage-commandlet.log"
        if ($LASTEXITCODE -ne 0) {throw "RSH grip surface $Stage failed."}
    }
    Write-Output "RSH_GRIP_SURFACE_STAGE_COMPLETE $Stage"
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
