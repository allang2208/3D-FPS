param([switch]$SkipBuild,[switch]$SkipImport,[string]$AssetScript='install_assets.py')
$ErrorActionPreference='Stop'
$releaseGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$releaseHeld=$false
function Set-ReleaseStatus([string]$Phase,[string]$Detail='') {
    @{phase=$Phase;detail=$Detail;updated_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build-status.json" -Encoding utf8
}
try {
    Set-ReleaseStatus 'waiting'
    try {$releaseHeld=$releaseGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$releaseHeld=$true}
    if (-not $releaseHeld) {throw 'UE batch queue timeout'}
    $releaseDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor holds the native DLL; preserve its session.'}
        $releaseBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $releaseBusy) {break}
        if ([DateTime]::UtcNow -ge $releaseDeadline) {throw 'An existing build or commandlet is still active'}
        Start-Sleep -Seconds 5
    } while ($true)
    if (-not $SkipBuild) {
        foreach ($releaseTarget in @('FPSGAMEEditor','FPSGAME')) {
            if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; preserving loaded DLL.'}
            Set-ReleaseStatus 'building' $releaseTarget
            & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $releaseTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> "$PSScriptRoot/build-$releaseTarget.log"
            if ($LASTEXITCODE -ne 0) {throw "Native build failed: $releaseTarget"}
        }
    }
    if ($SkipImport) {Set-ReleaseStatus 'complete' 'native build';Write-Output 'PANCHI_FLIGHT_NATIVE_BUILD_SAVED';return}
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; import through the current bridge.'}
    Set-ReleaseStatus 'importing'
    $releaseAssetScript=Join-Path $PSScriptRoot $AssetScript
    $releaseArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$releaseAssetScript",'-AllowCommandletRendering','-RenderOffscreen','-d3d12','-unattended','-nop4','-nosplash','-nosound',"-abslog=$PSScriptRoot/asset-import.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @releaseArgs *> "$PSScriptRoot/asset-import-console.log"
    if ($LASTEXITCODE -ne 0) {throw 'Material authoring failed; see asset-import.log'}
    Set-ReleaseStatus 'complete'
    if ($SkipBuild) {Write-Output 'PANCHI_RELEASE_ASSETS_SAVED'} else {Write-Output 'PANCHI_RELEASE_BUILD_AND_ASSETS_SAVED'}
} catch {
    Set-ReleaseStatus 'failed' $_.Exception.Message
    throw
} finally {
    if ($releaseHeld) {$releaseGate.ReleaseMutex()};$releaseGate.Dispose()
}
