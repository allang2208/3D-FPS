$ErrorActionPreference='Stop'
$previous=Join-Path $PSScriptRoot '../Wrist34'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'Existing UE batch retained'}
    $deadline=(Get-Date).AddMinutes(10)
    while(@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}).Count){
        if((Get-Date)-gt $deadline){throw 'Build still running; preserved'}
        Start-Sleep -Seconds 5
    }
    & "$previous/run-native.ps1" -Mode geometry -Label 'visual_wrist_closeup' -Manifest 'VisualReview/manifest_wrist_closeup.json'
    & "$previous/VisualReview/run.ps1" -SkipBuild -PrismOnly
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
