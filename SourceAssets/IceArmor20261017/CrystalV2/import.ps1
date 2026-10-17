$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskScript=Join-Path $taskRoot 'Tools/Skills/build_ice_armor_v2.py'
$taskLog=Join-Path $PSScriptRoot 'import.log'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskOwnsMutex=$false
try {
    while(-not $taskOwnsMutex) {
        try {$taskOwnsMutex=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskOwnsMutex=$true}
        if(-not $taskOwnsMutex){Write-Output 'Waiting for the existing UE asset batch.'}
    }
    # A Game target produces FPSGAME.exe and can compile alongside this asset
    # batch; only Editor builds replace the module DLL this commandlet loads.
    while($active=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat.*FPSGAMEEditor') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')})) {
        Write-Output ('Waiting for native build/commandlet PID '+($active.ProcessId -join ','))
        foreach($p in $active){Wait-Process -Id $p.ProcessId -ErrorAction SilentlyContinue}
    }
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME'}) {
        throw 'The project editor is running; use its existing batch bridge for this import.'
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ('-script='+$taskScript) -unattended -nullrhi -Multiprocess -NoAutoSDK -nosound -NoLiveCoding ('-abslog='+$taskLog) *> (Join-Path $PSScriptRoot 'import-console.log')
    $taskExit=$LASTEXITCODE
    Write-Output ('Ice armour asset import exit='+$taskExit)
    Get-Content -LiteralPath $taskLog -Tail 14
    exit $taskExit
} finally {
    if($taskOwnsMutex){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
