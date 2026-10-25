$ErrorActionPreference='Stop'
$beltProject='D:/FPS3D/FPSGAME'
$beltRoot="$beltProject/SourceAssets/BeltIcons20261025/ArcaneFrontR1"
$beltGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$beltHeld=$false
try {
    try {$beltHeld=$beltGate.WaitOne()} catch [Threading.AbandonedMutexException] {$beltHeld=$true}
    while ($true) {
        $beltProcesses=@(Get-CimInstance Win32_Process)
        if (@($beltProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count) {
            throw 'Preserve the running editor; use its asset bridge instead.'
        }
        $beltBusy=@($beltProcesses | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if (-not $beltBusy.Count) {break}
        try {Wait-Process -Id $beltBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $beltBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $beltStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $beltBuildLog="$beltRoot/build-editor-$beltStamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$beltProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=6 "-Log=$beltBuildLog" *> "$beltBuildLog.stdout.txt"
    $beltBuildCode=$LASTEXITCODE
    @{target='FPSGAMEEditor';exit_code=$beltBuildCode;log=$beltBuildLog;runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$beltRoot/build.json" -Encoding utf8
    Write-Output "Belt layout Editor build exit=$beltBuildCode"
    if ($beltBuildCode -ne 0) {Get-Content -LiteralPath "$beltBuildLog.stdout.txt" -Tail 18;throw 'Editor build failed; preserve other work'}
    if (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) {throw 'An editor appeared; save icons through the existing bridge.'}
    $beltAssetLog="$beltRoot/save-icons-$beltStamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$beltProject/FPSGAME.uproject" '-run=pythonscript' "-script=$beltProject/Tools/BeltIcons/save_icons.py" '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' "-abslog=$beltAssetLog" *> "$beltAssetLog.stdout.txt"
    $beltAssetCode=$LASTEXITCODE
    @{exit_code=$beltAssetCode;log=$beltAssetLog;runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$beltRoot/asset-execution.json" -Encoding utf8
    Write-Output "Belt UI asset save exit=$beltAssetCode"
    if ($beltAssetCode -ne 0) {Get-Content -LiteralPath "$beltAssetLog.stdout.txt" -Tail 18;throw 'Belt UI asset save failed'}
} finally {
    if ($beltHeld) {$beltGate.ReleaseMutex()}
    $beltGate.Dispose()
}
