# User-requested read-only checks. Neither batch saves assets or starts a game world.
param([switch]$ContractOnly)
$ErrorActionPreference='Stop'
$gardenProject='D:/FPS3D/FPSGAME'
$gardenAudit="$gardenProject/SourceAssets/EcologyGardener20261014/Audit"
$gardenExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$gardenMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$gardenHeld=$false
$gardenOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
$gardenResults=@()
if($ContractOnly -and (Test-Path "$gardenAudit/checks.json")) {
    $gardenResults=@(Get-Content "$gardenAudit/checks.json" -Raw|ConvertFrom-Json|Where-Object {$_.check -eq 'assets'})
}
try {
    while (-not $gardenHeld) {
        try {$gardenHeld=$gardenMutex.WaitOne(5000)}catch [Threading.AbandonedMutexException] {$gardenHeld=$true}
        if(-not $gardenHeld){continue}
        $gardenBuilds=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if(-not $gardenBuilds.Count){break}
        $gardenMutex.ReleaseMutex();$gardenHeld=$false;Start-Sleep -Seconds 10
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $gardenChecks=if($ContractOnly){@('TaskTrackingContract')}else{@('assets','TaskTrackingContract')}
    foreach($gardenCheck in $gardenChecks) {
        $gardenLog="$gardenAudit/$gardenCheck-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
        [string[]]$gardenArgs=if($gardenCheck -eq 'assets') {@('-run=pythonscript',"-script=$gardenProject/Tools/EcologyGardener/audit_assets.py")} else {@('-run=TaskTrackingContract')}
        Write-Output "ECOLOGY_AUDIT_STARTED $gardenCheck LOG=$gardenLog"
        & $gardenExe "$gardenProject/FPSGAME.uproject" @gardenArgs '-nullrhi' '-unattended' '-nop4' '-nosplash' '-nosound' "-abslog=$gardenLog" *> "$gardenLog.stdout"
        $gardenCode=$LASTEXITCODE
        $gardenResults+=@{check=$gardenCheck;exit_code=$gardenCode;log=$gardenLog}
        $gardenResults|ConvertTo-Json -Depth 4|Set-Content "$gardenAudit/checks.json" -Encoding utf8
        Write-Output "ECOLOGY_AUDIT_FINISHED $gardenCheck EXIT=$gardenCode"
    }
    if(@($gardenResults|Where-Object {$_.exit_code -ne 0}).Count){throw 'Ecology audit failed; see Audit/checks.json.'}
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$gardenOldSdk
    if($gardenHeld){$gardenMutex.ReleaseMutex()}
    $gardenMutex.Dispose()
}
