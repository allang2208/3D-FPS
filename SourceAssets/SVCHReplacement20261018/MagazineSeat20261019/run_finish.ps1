$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(1200))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch gate remained busy; no build or asset writes started.'}
    foreach($ueProcess in @(Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue)) {
        $command=(Get-CimInstance Win32_Process -Filter "ProcessId=$($ueProcess.Id)").CommandLine
        if($command -and $command.Replace('\','/').IndexOf("$taskProject/FPSGAME.uproject",[StringComparison]::OrdinalIgnoreCase) -ge 0){throw "Project modules are in use by PID $($ueProcess.Id); preserve it."}
    }
    $builds=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    if($builds.Count){throw 'Existing native build is active; preserve it.'}
    Write-Output 'SVCH_BUILD_STARTED'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 "-Log=$PSScriptRoot/build-editor.log" *> "$PSScriptRoot/build-console.log"
    if($LASTEXITCODE -ne 0){throw 'Editor build failed; see build-console.log.'}
    @{complete=$true;target='FPSGAMEEditor Win64 Development';completed_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_receipt.json"
    Write-Output 'SVCH_ASSET_SAVE_STARTED'
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/install_all.py" -unattended -nosplash -nosound -NullRHI "-abslog=$PSScriptRoot/install.log" *> "$PSScriptRoot/install-console.log"
    if($LASTEXITCODE -ne 0){throw 'Asset save failed; see install-console.log.'}
    Write-Output 'SVCH_MAGAZINE_DELIVERY_SAVED'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
