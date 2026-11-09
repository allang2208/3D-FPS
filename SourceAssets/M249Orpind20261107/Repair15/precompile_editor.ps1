$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$engine='E:/Program Files (x86)/UE_5.8/Engine'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Editor compile batch wait expired'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -like '*D:/FPS3D/FPSGAME/FPSGAME.uproject*'})
    if($editors.Count -ne 1){throw 'Expected one existing project editor'}
    # Compile Live Coding object files only. Do not overwrite the loaded base DLL
    # or change the LiveCodingConsole's global action limit.
    Copy-Item -LiteralPath "$engine/Intermediate/LiveCodingModules.json" -Destination "$PSScriptRoot/LiveCodingModules.json"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $log="$project/Saved/Logs/ScopeEyeRelief20261108EditorObjects.log"
    & "$engine/Build/BatchFiles/Build.bat" FPSGAMEEditor Win64 Development "-Project=$project/FPSGAME.uproject" -LiveCoding "-LiveCodingModules=$PSScriptRoot/LiveCodingModules.json" "-LiveCodingManifest=$PSScriptRoot/LiveCodingManifest.json" -WaitMutex -LiveCodingLimit=600 -MaxParallelActions=6 "-Log=$log" *> "$log.console"
    $code=$LASTEXITCODE
    @{exit_code=$code;target='FPSGAMEEditor';mode='LiveCoding objects only';log=$log;base_editor_dll_updated=$false;runtime_tested=$false;editor_pid=$editors[0].ProcessId} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/editor_objects_receipt.json" -Encoding utf8
    Get-Content -LiteralPath "$log.console" -Tail 12
    if($code -ne 0){throw "M249 editor object build exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
