param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$taskProject = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskProjectFile = Join-Path $taskProject 'FPSGAME.uproject'
$taskOutput = Join-Path $taskProject 'Saved/IceWallCondensation20261001'
[IO.Directory]::CreateDirectory($taskOutput) | Out-Null
$taskState = [ordered]@{ assetsSaved = $false; gameBuild = 'pending'; editorBuild = 'pending'; gameplayTested = $false }
function Write-TaskState {
    [IO.File]::WriteAllText((Join-Path $taskOutput 'delivery.json'), ($taskState | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
}
function Project-Editors {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        ($_.CommandLine -replace '\\','/') -match [regex]::Escape(($taskProjectFile -replace '\\','/'))
    })
}
function Wait-CompileWindow {
    do {
        $busyBuild = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='UnrealBuildTool.exe' OR Name='cl.exe' OR Name='link.exe'" | Where-Object {
            $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -in @('cl.exe','link.exe') -or $_.CommandLine -match 'UnrealBuildTool'
        })
        $busyCommandlets = @(Project-Editors | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' })
        if ($busyBuild.Count -or $busyCommandlets.Count) {
            Write-Host ('Waiting for existing build/asset processes: ' + (($busyBuild + $busyCommandlets | Select-Object -ExpandProperty ProcessId) -join ','))
            Start-Sleep -Seconds 15
        }
    } while ($busyBuild.Count -or $busyCommandlets.Count)
}
Write-TaskState
Wait-CompileWindow
$taskAuthor = Join-Path $PSScriptRoot 'author_ice_wall_condensation_20261001.py'
$guiEditors = @(Project-Editors | Where-Object { $_.Name -eq 'UnrealEditor.exe' })
if ($guiEditors.Count) {
    Write-Host 'Saving through the existing serialized editor bridge.'
    & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskAuthor -OutputFile (Join-Path $taskOutput 'asset-bridge-02.txt') -MaxOutputChars 3500
    if ($LASTEXITCODE -ne 0) { throw 'Asset bridge did not complete.' }
} else {
    Write-Host 'Saving assets in a background commandlet.'
    $taskCommandlet = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    & $taskCommandlet $taskProjectFile -run=pythonscript "-script=$taskAuthor" -unattended -nop4 -nosplash -NullRHI -nosound "-abslog=$(Join-Path $taskOutput 'asset-commandlet.log')" *> (Join-Path $taskOutput 'asset-commandlet-output.log')
    if ($LASTEXITCODE -ne 0) { throw "Asset commandlet failed: $LASTEXITCODE" }
}
foreach ($receipt in @('gather-authoring.json','landing-authoring.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskOutput $receipt))) { throw "Missing asset save receipt: $receipt" }
}
$taskState.assetsSaved = $true
Write-TaskState
Wait-CompileWindow
$taskBuild = Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat'
Write-Host 'Building FPSGAME Game target.'
& $taskBuild FPSGAME Win64 Development "-Project=$taskProjectFile" -NoHotReload -NoHotReloadFromIDE -DisableUnity -NoUBA -MaxParallelActions=4 "-Log=$(Join-Path $taskOutput 'build-game.log')"
if ($LASTEXITCODE -ne 0) { $taskState.gameBuild = 'failed'; Write-TaskState; throw 'Game build failed.' }
$taskState.gameBuild = 'succeeded'
Write-TaskState
Wait-CompileWindow
$lockedDll = $false
$taskDll = Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
try { $dllStream = [IO.File]::Open($taskDll, 'Open', 'ReadWrite', 'None'); $dllStream.Dispose() } catch { $lockedDll = $true }
if ((Project-Editors).Count -or $lockedDll) {
    $taskState.editorBuild = 'pending-editor-close'
    Write-TaskState
    Write-Host 'Assets and Game saved. Ordinary Editor build needs the editor closed.'
    exit 10
}
Write-Host 'Building FPSGAME ordinary Editor target.'
& $taskBuild FPSGAMEEditor Win64 Development "-Project=$taskProjectFile" -NoHotReload -NoHotReloadFromIDE "-Log=$(Join-Path $taskOutput 'build-editor.log')"
if ($LASTEXITCODE -ne 0) { $taskState.editorBuild = 'failed'; Write-TaskState; throw 'Editor build failed.' }
$taskState.editorBuild = 'succeeded'
Write-TaskState
Write-Host 'Ice-wall assets and ordinary Game/Editor builds saved. Gameplay testing remains with the user.'
