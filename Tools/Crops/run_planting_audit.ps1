$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$receipts=Join-Path $projectRoot 'SourceAssets\PlantingGameplay20261022'
$state=Get-Content -LiteralPath (Join-Path $receipts 'build-editor-status.json') -Raw | ConvertFrom-Json
if($state.state -ne 'succeeded'){throw 'Planting Editor build has not succeeded; no commandlet started.'}
$root=Join-Path $receipts ('AuditRun-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$mutex.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){Write-Output 'Asset batch busy; planting audit commandlet was not started.';exit 75}
    $arguments=@(('"'+(Join-Path $projectRoot 'FPSGAME.uproject')+'"'),'-run=ColdSteelPlantingAudit',
        '-unattended','-nop4','-nosplash','-nullrhi','-nosound','-multiprocess','-NoShaderCompile',
        ('-PlantingAuditRoot="'+$root+'"'),('-UserDir="'+(Join-Path $root 'User')+'"'),('-abslog="'+(Join-Path $root 'engine.log')+'"'))
    $job=Start-Process -FilePath 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    [IO.File]::WriteAllText((Join-Path $receipts 'audit-process.json'),(@{pid=$job.Id;root=$root;startUtc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Write-Output ('Started isolated planting audit PID '+$job.Id+'; root '+$root)
    $job.WaitForExit();$job.Refresh()
    [IO.File]::WriteAllText((Join-Path $receipts 'audit-status.json'),(@{exitCode=$job.ExitCode;root=$root;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    if(Test-Path -LiteralPath (Join-Path $root 'planting-audit.json')){
        $r=Get-Content -Raw -LiteralPath (Join-Path $root 'planting-audit.json')|ConvertFrom-Json
        Write-Output ('Planting audit checks='+$r.checks+' failures='+$r.failures)
    }
    exit $job.ExitCode
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
