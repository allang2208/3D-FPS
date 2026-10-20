$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch gate remained busy; no build was started.'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($busy.Count){throw 'An existing editor, commandlet or build is active. Preserve it and retry later.'}
    # FrozenHost owns separate copies of the modules. Inspect loaded filenames
    # instead of rejecting every process whose project has the same basename.
    foreach($ueProcess in @(Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue)) {
        $command=(Get-CimInstance Win32_Process -Filter "ProcessId=$($ueProcess.Id)").CommandLine
        if($command -and $command.Replace('\','/').IndexOf('D:/FPS3D/FPSGAME/FPSGAME.uproject',[StringComparison]::OrdinalIgnoreCase) -ge 0){throw "Current project is open in PID $($ueProcess.Id); preserve it."}
        $loaded=@($ueProcess.Modules | Where-Object {
            $_ -and $_.FileName -and ($_.FileName.StartsWith('D:\FPS3D\FPSGAME\Binaries\',[StringComparison]::OrdinalIgnoreCase) -or
            $_.FileName.StartsWith('D:\FPS3D\FPSGAME\Plugins\',[StringComparison]::OrdinalIgnoreCase))
        })
        if($loaded.Count){throw "Current project modules are loaded by PID $($ueProcess.Id); preserve it."}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=1 "-Log=$PSScriptRoot/build-editor.log" *> "$PSScriptRoot/build-console.log"
    if($LASTEXITCODE -ne 0){throw 'Editor build failed; see build-console.log.'}
    [ordered]@{complete=$true;target='FPSGAMEEditor Win64 Development';completed_utc=[DateTime]::UtcNow.ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_receipt.json" -Encoding utf8
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
