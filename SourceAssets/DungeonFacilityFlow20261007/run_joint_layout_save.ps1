$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld){
        try{$taskHeld=$taskMutex.WaitOne(5000)}
        catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    }
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(UnrealEditor|UnrealEditor-Cmd|LiveCodingConsole|cl|link)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($taskBusy.Count){throw 'Preserve active editor/build; no assets were written'}
    $taskLog=Join-Path $PSScriptRoot 'Receipts/joint-layout-save-20261008.log'
    $taskOutput=Join-Path $PSScriptRoot 'Receipts/joint-layout-save-stdout-20261008.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" '-run=pythonscript' "-script=$PSScriptRoot/save_joint_layout.py" '-nullrhi' '-unattended' '-nop4' '-nosplash' "-abslog=$taskLog" *> $taskOutput
    $taskCode=$LASTEXITCODE
    Write-Output "JOINT_LAYOUT_SAVE_EXIT=$taskCode"
    if($taskCode -eq 0){Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Receipts/joint-layout-save-20261008.json')}
    exit $taskCode
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
