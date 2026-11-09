param([string]$Script='read_assets.py')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch wait expired'}
    $deadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
        if($busy.Count){if([DateTime]::UtcNow -gt $deadline){throw 'Existing build retained'};Start-Sleep -Seconds 5}
    }while($busy.Count)
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -like '*D:/FPS3D/FPSGAME/FPSGAME.uproject*'})
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmssfff'
    if($editors.Count){
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$PSScriptRoot/$Script" -OutputFile "$project/Saved/M249ReloadReview/ReturnReview24_$Script.$stamp.bridge.txt" -MaxOutputChars 3000 -RequestTimeoutSeconds 1800
        if(!$?){throw 'Existing editor import failed'}
    }else{
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $log="$project/Saved/Logs/M249_ReturnReview24_$Script.$stamp.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -RenderOffscreen -NoSound -NoP4 "-abslog=$log" *> "$log.console"
        $code=$LASTEXITCODE
        Get-Content -LiteralPath $log -Tail 6
        if($code -ne 0){throw "M249 import commandlet exit $code"}
    }
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
