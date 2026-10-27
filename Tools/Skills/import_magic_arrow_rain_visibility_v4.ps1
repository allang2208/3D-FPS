$ErrorActionPreference='Stop'
$visibilityRoot='D:/FPS3D/FPSGAME'
$visibilityOut="$visibilityRoot/Saved/MagicArrowRain20261026/VisibilityV4"
[IO.Directory]::CreateDirectory($visibilityOut) | Out-Null
$visibilityGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$visibilityHeld=$false
try {
    try {$visibilityHeld=$visibilityGate.WaitOne([TimeSpan]::FromMinutes(10))} catch [Threading.AbandonedMutexException] {$visibilityHeld=$true}
    if(-not $visibilityHeld){throw 'UE authoring window is occupied'}
    $visibilityDeadline=[DateTime]::UtcNow.AddMinutes(10)
    while(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool|AutomationTool') -or $_.Name -eq 'cl.exe' }) {
        if([DateTime]::UtcNow -gt $visibilityDeadline){throw 'Existing build still active; preserved it'}
        Start-Sleep -Seconds 5
    }
    if(Get-CimInstance Win32_Process | Where-Object { ($_.Name -like 'UnrealEditor*' -or $_.Name -like 'FPSGAME*.exe') -and $_.CommandLine -match 'FPSGAME' }) {throw 'FPSGAME is still loaded; no binary or package was replaced'}
    foreach($visibilityTarget in @('FPSGAMEEditor','FPSGAME')) {
        $visibilityLog="$visibilityOut/build-$visibilityTarget.log"
        Write-Output "BUILD_START $visibilityTarget"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $visibilityTarget Win64 Development "$visibilityRoot/FPSGAME.uproject" -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 *> $visibilityLog
        $visibilityCode=$LASTEXITCODE
        Get-Content -LiteralPath $visibilityLog -Tail 6
        if($visibilityCode -ne 0){throw "Build $visibilityTarget failed: $visibilityCode"}
    }
    if(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'FPSGAME' }) {throw 'Code build saved; open editor requires the existing asset bridge'}
    Write-Output 'VISIBILITY_V4_ASSET_AUTHOR_START'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$visibilityRoot/FPSGAME.uproject" -run=pythonscript "-script=$visibilityRoot/Tools/Skills/build_magic_arrow_rain_visibility_v4.py" -unattended -nop4 -nosplash -nullrhi -multiprocess "-abslog=$visibilityOut/asset-author.log" *> "$visibilityOut/asset-author-console.log"
    $visibilityCode=$LASTEXITCODE
    Write-Output "ASSET_AUTHOR_EXIT_CODE $visibilityCode"
    Get-Content -LiteralPath "$visibilityOut/asset-author-console.log" -Tail 5
    if(Test-Path -LiteralPath "$visibilityOut/asset-receipt.json") {Get-Content -LiteralPath "$visibilityOut/asset-receipt.json"}
    if($visibilityCode -ne 0){throw "Author commandlet returned $visibilityCode; inspect its compiler and save result before delivery"}
} finally {
    if($visibilityHeld){$visibilityGate.ReleaseMutex()}
    $visibilityGate.Dispose()
}