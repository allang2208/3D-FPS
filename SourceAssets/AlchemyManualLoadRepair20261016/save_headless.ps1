$ErrorActionPreference='Stop'
$loadRoot='D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualLoadRepair20261016'
$loadGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$loadHeld=$false
$loadPreviousSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while (!$loadHeld) {
        try {$loadHeld=$loadGate.WaitOne([TimeSpan]::FromSeconds(45))}
        catch [Threading.AbandonedMutexException] {$loadHeld=$true}
        if (!$loadHeld) {Write-Output 'Waiting for the current UE asset batch.'}
    }
    while ($true) {
        $loadBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and
            ([string]::IsNullOrEmpty($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')) -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if (!$loadBusy.Count) {break}
        if ($loadBusy | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run=' }) {
            Write-Output 'Interactive editor is active; leaving it and its loaded assets untouched.'
            exit 75
        }
        Write-Output "Waiting for UE process $($loadBusy[0].ProcessId)."
        try {Wait-Process -Id $loadBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if (Get-Process -Id $loadBusy[0].ProcessId -ErrorAction SilentlyContinue) {throw}}
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=pythonscript' "-script=$loadRoot/repair_material_slots.py" `
        '-NullRHI' '-unattended' '-nop4' '-nosplash' '-nosound' "-abslog=$loadRoot/save.log" *> "$loadRoot/save-console.log"
    if ($LASTEXITCODE -ne 0) {throw 'Manual material save failed; see save.log'}
    Write-Output 'Corrected manual page material bindings saved.'
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$loadPreviousSdk
    if ($loadHeld) {$loadGate.ReleaseMutex()}
    $loadGate.Dispose()
}
