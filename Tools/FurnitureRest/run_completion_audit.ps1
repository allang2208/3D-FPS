param([ValidateSet('Build','Authority')][string]$Mode='Build',[string]$Run='audit-01')
$ErrorActionPreference='Stop'
$furnitureProject='D:/FPS3D/FPSGAME'
$furnitureOut="$furnitureProject/SourceAssets/FurnitureRest20261022/CompletionAudit20261025"
$furnitureGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$furnitureHeld=$false
try {
    try {$furnitureHeld=$furnitureGate.WaitOne()} catch [Threading.AbandonedMutexException] {$furnitureHeld=$true}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
    if($busy.Count){throw "Existing UE/build processes preserved: $($busy.ProcessId -join ',')"}
    if($Mode -eq 'Build'){
        foreach($target in @('FPSGAMEEditor','FPSGAME')){
            & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development "-Project=$furnitureProject/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$furnitureOut/$Run-$target.log" *> "$furnitureOut/$Run-$target-console.log"
            $code=$LASTEXITCODE
            @{target=$target;exit_code=$code;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$furnitureOut/$Run-$target.json" -Encoding utf8
            if($code -ne 0){throw "$target build failed; see $Run-$target-console.log"}
            Write-Output "$target build completed."
        }
    } else {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$furnitureProject/FPSGAME.uproject" -run=FurnitureRestAudit -nullrhi -unattended -nop4 -nosound -nosplash "-UserDir=$furnitureOut/IsolatedAuthority" "-Out=$furnitureOut/$Run-authority.json" "-abslog=$furnitureOut/$Run-authority.log" *> "$furnitureOut/$Run-authority-console.log"
        $code=$LASTEXITCODE
        @{exit_code=$code;completed=(Get-Date).ToString('o');real_network_transport_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$furnitureOut/$Run-authority-process.json" -Encoding utf8
        Write-Output "Authority commandlet exit: $code"
        if($code -ne 0){throw 'Authority audit failed; inspect its report and log.'}
    }
} finally {if($furnitureHeld){$furnitureGate.ReleaseMutex()};$furnitureGate.Dispose()}
