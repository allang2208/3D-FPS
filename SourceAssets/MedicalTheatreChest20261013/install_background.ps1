$ErrorActionPreference='Stop'
$chestProject='D:\FPS3D\FPSGAME'
$chestExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$chestMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$chestHeld=$false
$chestPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    Write-Output 'Medical theatre chest asset save queued.'
    while (-not $chestHeld) {
        try { $chestHeld=$chestMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $chestHeld=$true }
        if (-not $chestHeld) { continue }
        $chestProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe'")
        $chestEditors=@($chestProcesses | Where-Object {
            $_.Name -like 'UnrealEditor*' -and $_.CommandLine -match '(?i)D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject'
        })
        if ($chestEditors | Where-Object { $_.Name -eq 'UnrealEditor.exe' }) {
            throw 'The project editor is open; preserve its loaded map and use a later background save.'
        }
        $chestBuilds=@($chestProcesses | Where-Object { $_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        if (-not $chestEditors.Count -and -not $chestBuilds.Count) { break }
        $chestMutex.ReleaseMutex()
        $chestHeld=$false
        Start-Sleep -Seconds 15
    }
    $chestStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $chestLog=Join-Path $PSScriptRoot "Receipts/save-$chestStamp.log"
    $chestOutput=Join-Path $PSScriptRoot "Receipts/stdout-$chestStamp.log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "MEDICAL_CHEST_SAVE_STARTED LOG=$chestLog"
    & $chestExe (Join-Path $chestProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$(Join-Path $PSScriptRoot 'install.py')" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$chestLog" *> $chestOutput
    $chestCode=$LASTEXITCODE
    Write-Output "MEDICAL_CHEST_SAVE_FINISHED EXIT=$chestCode LOG=$chestLog"
    if ($chestCode -ne 0) { throw "Medical chest save failed: $chestLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$chestPreviousSDK
    if ($chestHeld) { $chestMutex.ReleaseMutex() }
    $chestMutex.Dispose()
}
