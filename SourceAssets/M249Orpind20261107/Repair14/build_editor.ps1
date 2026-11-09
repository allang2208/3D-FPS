$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Editor build batch wait expired'}
    $deadline=[DateTime]::UtcNow.AddMinutes(20)
    do {
        $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -like '*D:/FPS3D/FPSGAME/FPSGAME.uproject*'})
        if($editors.Count){if([DateTime]::UtcNow -gt $deadline){throw 'Existing editor retained; full build not started'};Start-Sleep -Seconds 5}
    }while($editors.Count)
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $log="$project/Saved/Logs/M249Repair14EditorBuild.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$project/FPSGAME.uproject" -NoHotReload -WaitMutex -MaxParallelActions=6 "-Log=$log" *> "$log.console"
    $code=$LASTEXITCODE
    @{exit_code=$code;target='FPSGAMEEditor';log=$log;base_editor_dll_updated=($code -eq 0);runtime_tested=$false;editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_editor_receipt.json" -Encoding utf8
    Get-Content -LiteralPath "$log.console" -Tail 12
    if($code -ne 0){throw "M249 Editor build exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
