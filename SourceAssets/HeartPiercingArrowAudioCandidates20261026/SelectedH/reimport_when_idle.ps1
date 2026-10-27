param([int]$WaitSeconds=1200)
$ErrorActionPreference='Stop'
$audioRoot='D:/FPS3D/FPSGAME'
$audioLogRoot="$audioRoot/Saved/HeartPiercingArrowAudio20261026/BalancedV4"
New-Item -ItemType Directory -Force -Path $audioLogRoot | Out-Null
$audioDeadline=[DateTime]::UtcNow.AddSeconds($WaitSeconds)
$audioAnnounced=$false

function Get-AudioAssetOwners {
    Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and (-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME')) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool|AutomationTool') -or
        ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat|RunUAT.bat')
    }
}

while($true) {
    if(@(Get-AudioAssetOwners).Count) {
        if(-not $audioAnnounced) { Write-Output 'Waiting for the active editor/cook/build; the loaded sound asset is preserved.'; $audioAnnounced=$true }
        if([DateTime]::UtcNow -ge $audioDeadline) { throw 'Asset owner is still active; authored BalancedV4 is saved, reimport remains pending.' }
        Start-Sleep -Seconds 5
        continue
    }
    $audioGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $audioHeld=$false
    try {
        try { $audioHeld=$audioGate.WaitOne([TimeSpan]::FromSeconds(30)) }
        catch [Threading.AbandonedMutexException] { $audioHeld=$true }
        if(-not $audioHeld) {
            if([DateTime]::UtcNow -ge $audioDeadline) { throw 'UE batch is occupied; reimport remains pending.' }
            continue
        }
        if(@(Get-AudioAssetOwners).Count) { continue }
        $audioScript="$PSScriptRoot/import_audio.py"
        $audioLog="$audioLogRoot/import.log"
        Write-Output 'Reimporting only the heart-piercing release SoundWave.'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$audioRoot/FPSGAME.uproject" -run=pythonscript "-script=$audioScript" -unattended -nop4 -nosplash -nullrhi "-abslog=$audioLog" *> "$audioLogRoot/import-console.log"
        $audioExit=$LASTEXITCODE
        Get-Content -LiteralPath "$audioLogRoot/import-console.log" -Tail 8
        if($audioExit -ne 0) { throw "Audio reimport exited $audioExit; see $audioLog" }
        Write-Output 'Audio reimport finished; no gameplay test or C++ build was run.'
        break
    } finally {
        if($audioHeld) { $audioGate.ReleaseMutex() }
        $audioGate.Dispose()
    }
}
