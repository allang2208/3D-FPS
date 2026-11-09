$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(25))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Shared build window wait expired'}
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        if($busy.Count){Start-Sleep -Seconds 5}
    } while($busy.Count)
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -like '*D:/FPS3D/FPSGAME/FPSGAME.uproject*'})
    if($editors.Count){throw 'Existing project editor preserved; full build not started'}
    $started=Get-Date -Format o
    & dotnet 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll' FPSGAMEEditor Win64 Development "-Project=$project/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$PSScriptRoot/build_editor.log" *> "$PSScriptRoot/build_editor.txt"
    $code=$LASTEXITCODE
    @{started=$started;finished=(Get-Date -Format o);target='FPSGAMEEditor';exit_code=$code;editor_started=$false;runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_receipt.json"
    Get-Content -LiteralPath "$PSScriptRoot/build_editor.txt" -Tail 10
    if($code -ne 0){throw "Editor build failed: $code"}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
