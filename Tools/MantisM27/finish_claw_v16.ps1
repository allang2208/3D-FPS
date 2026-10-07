param([int]$QueueWaitSeconds=600)
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$engine='E:/Program Files (x86)/UE_5.8'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$locked=$false
try {
    try {$locked=$gate.WaitOne($QueueWaitSeconds*1000)} catch [Threading.AbandonedMutexException] {$locked=$true}
    if(!$locked){throw 'UE batch is occupied; retry without interrupting it.'}
    $deadline=(Get-Date).AddMinutes(12)
    do {
        $active=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -like 'UnrealEditor*' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(@($active | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Use the existing editor through the batch bridge; no process was stopped.'}
        if(!$active.Count){break}
        if((Get-Date)-gt $deadline){throw 'Existing background UE operation still holds the modules. Preserve it and retry later.'}
        Write-Output 'Waiting for the current background UE operation to finish.'
        foreach($item in $active){$running=Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue;if($running){[void]$running.WaitForExit(60000)}}
    } while($true)
    $arguments=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"','-unattended','-nop4','-nosplash','-nullrhi','-nosound',
        '-run=pythonscript','-script="D:/FPS3D/FPSGAME/Tools/MantisM27/import_claw_v16.py"',
        '-ExecCmds="Editor.AsyncSkinnedAssetCompilation 0"',
        '-abslog="D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV16/import.log"')
    $import=Start-Process -FilePath "$engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $import.WaitForExit();$import.Refresh()
    if($import.ExitCode -ne 0){throw "M27 ClawV16 import failed: $($import.ExitCode)"}
    Write-Output 'M27 ClawV16 imported and saved. No editor UI or gameplay test started.'
} finally {if($locked){$gate.ReleaseMutex()};$gate.Dispose()}
