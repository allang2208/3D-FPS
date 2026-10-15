param([switch]$SkipBuild,[switch]$ImpairedNetwork)
$ErrorActionPreference='Stop'
$validationRoot='D:\FPS3D\FPSGAME\SourceAssets\HeQueBoss20261014\DungeonE2E'
$validationMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$validationHeld=$false
try {
    while(-not $validationHeld) {
        try{$validationHeld=$validationMutex.WaitOne(5000)}catch [Threading.AbandonedMutexException]{$validationHeld=$true}
    }
    if(-not (Test-Path -LiteralPath "$validationRoot\Records\layout-bank-install.json")){throw 'The verified layout bank has not been saved yet.'}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'}){throw 'Editor reopened; preserve the active session.'}
    Write-Output 'DUNGEON_VALIDATION_WINDOW_ACQUIRED'
    if(-not $SkipBuild){& "$PSScriptRoot\build.ps1" -RecordsRoot $validationRoot}
    if($ImpairedNetwork){& "$PSScriptRoot\run_dungeon_audit.ps1" -LagMS 80 -LossPercent 2}
    else{& "$PSScriptRoot\run_dungeon_audit.ps1"}
} finally {
    if($validationHeld){$validationMutex.ReleaseMutex()}
    $validationMutex.Dispose()
}
