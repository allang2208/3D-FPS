param([string]$Script='install.py',[switch]$UnloadedTargetsConfirmed,[string]$RecordsRoot='D:\FPS3D\FPSGAME\SourceAssets\HeQueBoss20261014\RigV01')
$ErrorActionPreference='Stop'
$hequeProject='D:\FPS3D\FPSGAME'
$hequeRoot=$RecordsRoot
$hequeExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$hequeMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$hequeHeld=$false
$hequeSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while(-not $hequeHeld) {
        try {$hequeHeld=$hequeMutex.WaitOne(5000)}catch [Threading.AbandonedMutexException] {$hequeHeld=$true}
        if(-not $hequeHeld){continue}
        $hequeProcesses=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe'")
        if(-not $UnloadedTargetsConfirmed -and ($hequeProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME.uproject'})){throw 'Project editor is open; preserve loaded assets or establish that these isolated target packages are not loaded.'}
        # This production batch only creates /Game/Monsters/HeQue packages.
        # Keep the established asset mutex and DLL-build exclusion. Independent
        # commandlets reading/writing other package roots do not own these new
        # assets and must not indefinitely starve this batch between lock turns.
        $hequeBusy=@($hequeProcesses|Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'HeQue')})
        if(-not $hequeBusy.Count){break}
        $hequeMutex.ReleaseMutex();$hequeHeld=$false;Start-Sleep -Seconds 10
    }
    $hequeLog=Join-Path $hequeRoot ('Records/import-'+[IO.Path]::GetFileNameWithoutExtension($Script)+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "IMPORT_STARTED $hequeLog"
    & $hequeExe (Join-Path $hequeProject 'FPSGAME.uproject') '-run=pythonscript' ('-script='+ (Join-Path $hequeProject ('Tools\HeQue\'+$Script))) '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' ('-abslog='+$hequeLog) *> ($hequeLog+'.stdout')
    Write-Output "IMPORT_FINISHED EXIT=$LASTEXITCODE LOG=$hequeLog"
    if($LASTEXITCODE -ne 0){throw "Commandlet failed: $hequeLog"}
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$hequeSDK
    if($hequeHeld){$hequeMutex.ReleaseMutex()}
    $hequeMutex.Dispose()
}
