param([string]$ScriptPath='D:/FPS3D/FPSGAME/Tools/RootCrown/install.py',[switch]$WithRenderingRhi)
$ErrorActionPreference='Stop'
$rigProject='D:\FPS3D\FPSGAME'
$rigExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$rigMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$rigHeld=$false
$rigPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while(-not $rigHeld) {
        try {$rigHeld=$rigMutex.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$rigHeld=$true}
        if(-not $rigHeld){continue}
        $rigProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe'")
        $rigEditors=@($rigProcesses | Where-Object {$_.Name -like 'UnrealEditor*' -and $_.CommandLine -match '(?i)D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject'})
        if($rigEditors | Where-Object {$_.Name -eq 'UnrealEditor.exe'}){throw 'Project editor reopened; preserve its loaded assets and use the existing bridge.'}
        $rigBuilds=@($rigProcesses | Where-Object {$_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $rigEditors.Count -and -not $rigBuilds.Count){break}
        $rigMutex.ReleaseMutex();$rigHeld=$false;Start-Sleep -Seconds 10
    }
    $rigStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $rigLog=Join-Path $PSScriptRoot "Reports/import-$rigStamp.log"
    $rigOutput=Join-Path $PSScriptRoot "Reports/import-$rigStamp-stdout.log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "ROOT_CROWN_IMPORT_STARTED LOG=$rigLog"
    $rigRhi=if($WithRenderingRhi){@('-d3d12','-sm6','-RenderOffscreen','-AllowCommandletRendering','-nosound')}else{@('-nullrhi')}
    & $rigExe (Join-Path $rigProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$ScriptPath" '-unattended' '-nop4' '-nosplash' @rigRhi "-abslog=$rigLog" *> $rigOutput
    $rigCode=$LASTEXITCODE
    Write-Output "ROOT_CROWN_IMPORT_FINISHED EXIT=$rigCode LOG=$rigLog"
    if($rigCode -ne 0){throw "Root Crown import failed: $rigLog"}
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$rigPreviousSDK
    if($rigHeld){$rigMutex.ReleaseMutex()}
    $rigMutex.Dispose()
}
