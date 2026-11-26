param([Parameter(Mandatory=$true)][string]$Stage,[int]$Batches=1)
$ErrorActionPreference='Stop'
$contactRoot='D:/FPS3D/FPSGAME'
$contactWork=Join-Path $contactRoot 'SourceAssets/KaitlinWeaponContacts20261024'
$contactGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$contactHeld=$false
try {
    try {$contactHeld=$contactGate.WaitOne()} catch [Threading.AbandonedMutexException] {$contactHeld=$true}
    $contactBusy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($contactBusy.Count){Write-Output 'Existing editor/build preserved; use its Python gate or wait for this window.';exit 75}
    for($contactBatch=0;$contactBatch -lt $Batches;$contactBatch++) {
        $contactLog=Join-Path $contactWork ($Stage+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.log')
        Write-Output ('Asset batch: '+$contactLog)
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $contactRoot 'FPSGAME.uproject') '-run=pythonscript' ('-script='+(Join-Path $contactRoot ('Tools/KaitlinPlayer/'+$Stage+'.py'))) '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$contactLog) *> ($contactLog+'.stdout.txt')
        $contactExit=$LASTEXITCODE
        Get-Content -LiteralPath ($contactLog+'.stdout.txt') -Tail 5
        if($contactExit -ne 0){exit $contactExit}
    }
} finally {if($contactHeld){$contactGate.ReleaseMutex()};$contactGate.Dispose()}
