param([switch]$SkipBuild,[int]$QueueWaitSeconds=600)
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$engine='E:/Program Files (x86)/UE_5.8'
$out=Join-Path $project 'SourceAssets/MantisM27/AudioV1'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$locked=$false
try {
    try {$locked=$gate.WaitOne($QueueWaitSeconds*1000)} catch [Threading.AbandonedMutexException] {$locked=$true}
    if(!$locked){throw 'UE batch is occupied; retry without interrupting it.'}
    $deadline=(Get-Date).AddMinutes(15)
    do {
        $active=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -like 'UnrealEditor*' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(@($active | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Save and close the existing editor before the on-disk native build. No process was stopped.'}
        if(!$active.Count){break}
        if((Get-Date)-gt $deadline){throw 'Background UE operation is still active; preserve it and retry later.'}
        Write-Output 'Waiting for the current background UE operation to finish.'
        foreach($item in $active){$running=Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue;if($running){[void]$running.WaitForExit(60000)}}
    } while($true)
    if(!$SkipBuild){
        foreach($target in @('FPSGAMEEditor','FPSGAME')){
            & "$engine/Engine/Build/BatchFiles/Build.bat" $target Win64 Development "-Project=$project/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$out/build_$target.log"
            if($LASTEXITCODE -ne 0){throw "$target build failed: $LASTEXITCODE"}
        }
    }
    $arguments=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"','-unattended','-nop4','-nosplash','-nullrhi','-nosound',
        '-run=pythonscript','-script="D:/FPS3D/FPSGAME/Tools/MantisM27/import_audio_v1.py"',
        '-ExecCmds="Editor.AsyncSkinnedAssetCompilation 0"',
        '-abslog="D:/FPS3D/FPSGAME/SourceAssets/MantisM27/AudioV1/import.log"')
    $import=Start-Process -FilePath "$engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $import.WaitForExit();$import.Refresh()
    if($import.ExitCode -ne 0){throw "M27 AudioV1 import failed: $($import.ExitCode)"}
    $receipt=Get-Content -LiteralPath (Join-Path $out 'asset_receipt.json') -Raw | ConvertFrom-Json
    if(!$receipt.complete){throw 'The M27 audio import did not finish saving.'}
    Write-Output 'M27 AudioV1 built and saved: 15 SoundWaves and Blueprint. No editor UI, listening or gameplay test started.'
} finally {if($locked){$gate.ReleaseMutex()};$gate.Dispose()}
