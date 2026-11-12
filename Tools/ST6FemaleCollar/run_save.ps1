param([string]$ReceiptName='background-save-01')
$ErrorActionPreference='Stop'
$st6Project='D:/FPS3D/FPSGAME'
$st6Root=Join-Path $st6Project 'SourceAssets/ST6FemaleCollar20261108'
$st6Script=Join-Path $st6Project 'Tools/ST6FemaleCollar/save_assets.py'
$st6Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$st6Held=$false
try {
    try {$st6Held=$st6Gate.WaitOne()} catch [Threading.AbandonedMutexException] {$st6Held=$true}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Use the existing editor bridge for this save batch.'}
    while($true){
        $st6Build=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $st6Build.Count){break}
        try {Wait-Process -Id $st6Build[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
    }
    for($st6Batch=0;$st6Batch -lt 3;$st6Batch++){
        if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Editor opened; preserve it and use the bridge.'}
        $st6Log=Join-Path $st6Root ($ReceiptName+'-'+$st6Batch+'.log')
        if(Test-Path -LiteralPath $st6Log){throw 'Use a new receipt name.'}
        Write-Output ('ST6_SAVE_LOG '+$st6Log)
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $st6Project 'FPSGAME.uproject') '-run=pythonscript' ('-script='+$st6Script) '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$st6Log) *> ($st6Log+'.stdout.txt')
        $st6Code=$LASTEXITCODE
        Get-Content -LiteralPath ($st6Log+'.stdout.txt') -Tail 8
        if($st6Code -ne 0){exit $st6Code}
        $st6Receipt=Get-Content -LiteralPath (Join-Path $st6Root 'saved_assets.json') -Raw | ConvertFrom-Json
        if($st6Receipt.completed){break}
    }
} finally {
    if($st6Held){$st6Gate.ReleaseMutex()}
    $st6Gate.Dispose()
}
