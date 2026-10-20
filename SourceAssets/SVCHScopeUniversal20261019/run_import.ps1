$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    Write-Output 'KV_SCOPE_IMPORT_WAITING'
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(1200))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(!$held){throw 'UE batch gate remained busy; import not started.'}
    foreach($kvProcess in @(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')})){
        if($kvProcess.CommandLine -and $kvProcess.CommandLine.Replace('\','/').Contains('D:/FPS3D/FPSGAME')){
            # A commandlet may still be shutting down after releasing its batch.
            # Wait for natural exit, never terminate it or open a second editor.
            if($kvProcess.Name -eq 'UnrealEditor-Cmd.exe'){
                Wait-Process -Id $kvProcess.ProcessId -Timeout 60 -ErrorAction SilentlyContinue
                if(!(Get-Process -Id $kvProcess.ProcessId -ErrorAction SilentlyContinue)){continue}
            }
            throw "Preserve active project process $($kvProcess.ProcessId)"
        }
    }
    Write-Output 'KV_SCOPE_IMPORT_STARTED'
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$PSScriptRoot/install_assets.py" -unattended -nosplash -nosound -NullRHI "-abslog=$PSScriptRoot/install-resume.log" *> "$PSScriptRoot/install-resume-console.log"
    if($LASTEXITCODE -ne 0){throw 'KV import failed; inspect install-resume-console.log'}
    @{complete=$true;time_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/import_resume_receipt.json"
    Write-Output 'KV_SCOPE_IMPORT_COMPLETE'
}catch{
    @{complete=$false;error=$_.Exception.Message;time_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/import_resume_error.json"
    throw
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
