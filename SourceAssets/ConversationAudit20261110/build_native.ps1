param([switch]$BowOnly,[switch]$ReadAssets)
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no build or test started.'}
    $deadline=[DateTime]::UtcNow.AddMinutes(20)
    while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') }).Count){
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing background work preserved; wait timed out.'};Start-Sleep -Seconds 3
    }
    if(Get-Process UnrealEditor,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing editor/game preserved.'}
    & ($root+'/Tools/Build/Build-Editor.ps1') *> ($PSScriptRoot+'/build.log')
    if($LASTEXITCODE -ne 0){throw 'Build failed.'}
    $run=Join-Path $PSScriptRoot ('Native/'+(Get-Date -Format 'yyyyMMdd-HHmmss'));New-Item -ItemType Directory -Force -Path $run | Out-Null
    $cases=if($BowOnly){@('BowPresentationReview')}else{@('BowPresentationReview','BallisticOnly')}
    foreach($case in $cases){
        $command=if($case -eq 'BowPresentationReview'){'BowSkillTrainingAudit'}else{'LeapStrikeAudit'}
        $out=Join-Path $run $case;New-Item -ItemType Directory -Force -Path $out | Out-Null
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' ($root+'/FPSGAME.uproject') ('-run='+$command) ('-'+$case) ('-ReportDir='+$out) ('-Out='+$out) -nullrhi -nosound -unattended -nosplash -nop4 ('-abslog='+$out+'/engine.log') *> ($out+'/stdout.log')
        $code=$LASTEXITCODE
        @{case=$case;exit_code=$code;dll_sha256=(Get-FileHash ($root+'/Binaries/Win64/UnrealEditor-FPSGAME.dll')).Hash} | ConvertTo-Json | Set-Content ($out+'/receipt.json') -Encoding utf8
        Write-Output "NATIVE_RESULT $case exit=$code path=$out"
    }
    if($ReadAssets){& ($PSScriptRoot+'/read_assets.ps1')}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
