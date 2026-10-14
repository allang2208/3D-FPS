# User-requested data checks only; no map, game, rendering or asset save.
$ErrorActionPreference='Stop'
$ecologyProject='D:/FPS3D/FPSGAME'
$ecologyExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$ecologyMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$ecologyHeld=$false
$ecologyPreviousSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while (-not $ecologyHeld) {
        try { $ecologyHeld=$ecologyMutex.WaitOne(5000) }
        catch [Threading.AbandonedMutexException] { $ecologyHeld=$true }
        if (-not $ecologyHeld) { continue }
        $ecologyProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe'")
        $ecologyEditors=@($ecologyProcesses | Where-Object {$_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'FPSGAME.uproject'})
        if ($ecologyEditors | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) { throw 'Preserve the running project editor.' }
        $ecologyBuilds=@($ecologyProcesses | Where-Object {$_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if (-not $ecologyEditors.Count -and -not $ecologyBuilds.Count) { break }
        $ecologyMutex.ReleaseMutex();$ecologyHeld=$false;Start-Sleep -Seconds 10
    }
    $ecologyStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $ecologyLog=Join-Path $ecologyProject "SourceAssets/RootCrown20261014/Reports/ecology-contract-$ecologyStamp.log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "ECOLOGY_CONTRACT_STARTED LOG=$ecologyLog"
    & $ecologyExe "$ecologyProject/FPSGAME.uproject" '-run=TaskTrackingContract' '-nullrhi' '-unattended' '-nop4' '-nosplash' "-abslog=$ecologyLog" *> "$ecologyLog.stdout"
    $ecologyCode=$LASTEXITCODE
    @{exit_code=$ecologyCode;log=$ecologyLog;finished=(Get-Date -Format o)} | ConvertTo-Json |
        Set-Content -LiteralPath "$ecologyProject/SourceAssets/RootCrown20261014/Reports/ecology-contract.json" -Encoding utf8
    Write-Output "ECOLOGY_CONTRACT_FINISHED EXIT=$ecologyCode LOG=$ecologyLog"
    if ($ecologyCode -ne 0) { throw "Data contract failed: $ecologyLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$ecologyPreviousSdk
    if ($ecologyHeld) { $ecologyMutex.ReleaseMutex() }
    $ecologyMutex.Dispose()
}
