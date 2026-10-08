param([switch]$SkipBuild,[switch]$SkipAssets,[string[]]$AssetScripts=@('author_assets.py','compile_motes.py'))
$ErrorActionPreference='Stop'
$visibilityGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$visibilityHeld=$false
function Set-VisibilityStatus([string]$Phase,[string]$Detail='') {
    @{phase=$Phase;detail=$Detail;updated_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build-status.json" -Encoding utf8
}
try {
    Set-VisibilityStatus 'waiting'
    try {$visibilityHeld=$visibilityGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$visibilityHeld=$true}
    if (-not $visibilityHeld) {throw 'UE batch queue timeout'}
    $visibilityDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor holds the native DLL; preserve its session.'}
        $visibilityBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $visibilityBusy) {break}
        if ([DateTime]::UtcNow -ge $visibilityDeadline) {throw 'An existing build or commandlet is still active'}
        Start-Sleep -Seconds 5
    } while ($true)
    if (-not $SkipBuild) {
        foreach ($visibilityTarget in @('FPSGAMEEditor','FPSGAME')) {
            if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; preserving loaded DLL.'}
            Set-VisibilityStatus 'building' $visibilityTarget
            & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $visibilityTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> "$PSScriptRoot/build-$visibilityTarget.log"
            if ($LASTEXITCODE -ne 0) {throw "Native build failed: $visibilityTarget"}
        }
    }
    if (-not $SkipAssets) {
        foreach ($visibilityScript in $AssetScripts) {
            if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; preserve loaded assets.'}
            Set-VisibilityStatus 'saving' $visibilityScript
            $visibilityScriptPath=Join-Path $PSScriptRoot $visibilityScript
            $visibilityArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$visibilityScriptPath",'-AllowCommandletRendering','-RenderOffscreen','-d3d12','-unattended','-nop4','-nosplash','-nosound',"-abslog=$PSScriptRoot/$visibilityScript.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
            if ($visibilityScript -eq 'compile_motes.py') {$visibilityArgs+='-ForceDPCVars=fx.ForceCompileOnLoad=1'}
            & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @visibilityArgs *> "$PSScriptRoot/$visibilityScript.console.log"
            if ($LASTEXITCODE -ne 0) {throw "Asset authoring failed: $visibilityScript"}
        }
    }
    Set-VisibilityStatus 'complete'
    Write-Output 'ZHENMO_VISIBILITY_BUILD_AND_SAVE_COMPLETE'
} catch {
    Set-VisibilityStatus 'failed' $_.Exception.Message
    throw
} finally {
    if ($visibilityHeld) {$visibilityGate.ReleaseMutex()};$visibilityGate.Dispose()
}
