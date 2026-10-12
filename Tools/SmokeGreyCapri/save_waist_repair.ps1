param([int]$QueueWaitSeconds=300)
$ErrorActionPreference='Stop'
$waistProject='D:/FPS3D/FPSGAME'
$waistRoot="$waistProject/SourceAssets/PlayerWaistSeam20261012"
$waistGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$waistHeld=$false
try {
    try { $waistHeld=$waistGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) } catch [Threading.AbandonedMutexException] { $waistHeld=$true }
    if (-not $waistHeld) { throw 'An existing UE authoring batch is still running.' }
    $waistDeadline=[DateTime]::UtcNow.AddMinutes(15)
    $waistWaiting=$false
    while (Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')
    }) {
        if (-not $waistWaiting) { Write-Output 'Waiting for the active build or commandlet to finish.'; $waistWaiting=$true }
        if ([DateTime]::UtcNow -gt $waistDeadline) { throw 'The active build or commandlet has not finished; no packages were modified.' }
        Start-Sleep -Seconds 10
    }
    $waistEditor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }
    if ($waistEditor) { throw 'The active editor must use the asset bridge; no packages were modified.' }
    foreach ($waistRelative in @(
        'Content/Characters/ModularOutfit20260924/SmokeGreyCapri20261004/SK_Jason_SmokeGreyCapri.uasset',
        'Content/Characters/ModularOutfit20260924/SmokeGreyCapri20261004/SK_Jason_SmokeGreyCapri_HighBootsFit.uasset',
        'SourceAssets/SmokeGreyCapri20261004/Jason_SmokeGreyCapri.json',
        'SourceAssets/SmokeGreyCapri20261004/Jason_SmokeGreyCapri_HighBootsFit.json'
    )) {
        $waistBackup=Join-Path "$waistProject/trash/player-presentation-retired-20261012/SourceAssets/PlayerWaistSeam20261012/Before" $waistRelative
        if (-not (Test-Path -LiteralPath $waistBackup)) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $waistBackup) -Force | Out-Null
            Copy-Item -LiteralPath (Join-Path $waistProject $waistRelative) -Destination $waistBackup
        }
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$waistProject/FPSGAME.uproject" -run=pythonscript "-script=$waistProject/Tools/SmokeGreyCapri/save_waist_repair.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$waistRoot/save-waist.log" *> "$waistRoot/save-waist-console.txt"
    if ($LASTEXITCODE -ne 0) { throw "Waist asset save failed; see $waistRoot/save-waist.log." }
    Write-Output 'CAPRI_WAIST_BACKGROUND_SAVED'
} finally {
    if ($waistHeld) { $waistGate.ReleaseMutex() }
    $waistGate.Dispose()
}
