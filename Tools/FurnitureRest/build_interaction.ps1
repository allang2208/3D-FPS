param([string]$Run='build-01')
$ErrorActionPreference='Stop'
$furnitureProject='D:/FPS3D/FPSGAME'
$furnitureOut="$furnitureProject/SourceAssets/FurnitureRest20261022/ApartmentIntegration20261024"
$furnitureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$furnitureHeld=$false
try {
    Write-Output 'Waiting for the shared UE build window.'
    try {$furnitureHeld=$furnitureGate.WaitOne()} catch [Threading.AbandonedMutexException] {$furnitureHeld=$true}
    while($true){
        $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $busy.Count){break}
        if($busy | Where-Object {$_.Name -eq 'UnrealEditor.exe'}){throw 'Existing editor preserved. The ordinary DLL build needs the editor closed.'}
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    foreach($target in @('FPSGAMEEditor','FPSGAME')){
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development "-Project=$furnitureProject/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$furnitureOut/$Run-$target.log" *> "$furnitureOut/$Run-$target-console.log"
        $code=$LASTEXITCODE
        @{target=$target;exit_code=$code;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$furnitureOut/$Run-$target.json" -Encoding utf8
        if($code -ne 0){throw "$target build failed; see $furnitureOut/$Run-$target-console.log"}
        Write-Output "$target build completed."
    }
} finally {if($furnitureHeld){$furnitureGate.ReleaseMutex()};$furnitureGate.Dispose()}