param([string]$Run='build-01')
$ErrorActionPreference='Stop'
$doubleProject='D:/FPS3D/FPSGAME'
$doubleOut="$doubleProject/SourceAssets/FurnitureRest20261022/DoubleOccupancy20261025"
$doubleGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$doubleHeld=$false
try {
    Write-Output 'Waiting for the shared UE build window.'
    try {$doubleHeld=$doubleGate.WaitOne()} catch [Threading.AbandonedMutexException] {$doubleHeld=$true}
    while($true){
        $doubleBusy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $doubleBusy.Count){break}
        if($doubleBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe'}){throw 'Existing editor preserved; close it before the reflected layout build.'}
        try {Wait-Process -Id $doubleBusy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $doubleBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    foreach($doubleTarget in @('FPSGAMEEditor','FPSGAME')){
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $doubleTarget Win64 Development "-Project=$doubleProject/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$doubleOut/$Run-$doubleTarget.log" *> "$doubleOut/$Run-$doubleTarget-console.log"
        $doubleCode=$LASTEXITCODE
        @{target=$doubleTarget;exit_code=$doubleCode;completed=(Get-Date).ToString('o');runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$doubleOut/$Run-$doubleTarget-receipt.json" -Encoding utf8
        if($doubleCode -ne 0){throw "$doubleTarget failed; see $doubleOut/$Run-$doubleTarget-console.log"}
        Write-Output "$doubleTarget build completed."
    }
} finally {if($doubleHeld){$doubleGate.ReleaseMutex()};$doubleGate.Dispose()}
