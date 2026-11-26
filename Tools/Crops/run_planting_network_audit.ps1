param([switch]$RunAuthorizedRegression)
$ErrorActionPreference='Stop'
if(-not $RunAuthorizedRegression){throw 'Explicit regression authorization is required.'}
$project='D:\FPS3D\FPSGAME'
$exe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$dll=Join-Path $project 'Binaries\Win64\UnrealEditor-FPSGAME.dll'
$sources=@('Source\FPSGAME\Building\ColdSteelPlantingNetworkAudit.cpp','Source\FPSGAME\Building\ColdSteelPlantingNetwork.cpp','Source\FPSGAME\Building\ColdSteelPlantingTypes.h')
foreach($source in $sources){if((Get-Item (Join-Path $project $source)).LastWriteTimeUtc -gt (Get-Item $dll).LastWriteTimeUtc){throw 'Build the final Editor DLL before running this regression.'}}
$root=Join-Path $project ('SourceAssets\PlantingMultiplayer20261022\TestRuns\NetworkOrder-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
function Get-ProductionSaves {
    $saved=Join-Path $project 'Saved\SaveGames'
    @(Get-ChildItem -LiteralPath $saved -File -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName | ForEach-Object {
        [ordered]@{path=$_.FullName;length=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
    }) | ConvertTo-Json -Depth 5 -Compress
}
$before=Get-ProductionSaves
[IO.File]::WriteAllText((Join-Path $root 'production-saves-before.json'),$before,[Text.UTF8Encoding]::new($false))
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$mutex.WaitOne([TimeSpan]::FromSeconds(60))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Editor asset batch is busy; no regression started.'}
    $arguments=@(('"'+(Join-Path $project 'FPSGAME.uproject')+'"'),'-run=ColdSteelPlantingAudit','-PlantingNetworkAudit',
        '-unattended','-nop4','-nosplash','-nullrhi','-nosound','-multiprocess','-NoShaderCompile',
        ('-PlantingAuditRoot="'+$root+'"'),('-UserDir="'+(Join-Path $root 'User')+'"'),('-abslog="'+(Join-Path $root 'engine.log')+'"'))
    $job=Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden -PassThru
    [IO.File]::WriteAllText((Join-Path $root 'launch.json'),(@{pid=$job.Id;executable=$exe;arguments=$arguments}|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
    Write-Output ('Planting network-branch regression PID '+$job.Id+'; root '+$root)
    $job.WaitForExit();$job.Refresh();$after=Get-ProductionSaves
    [IO.File]::WriteAllText((Join-Path $root 'production-saves-after.json'),$after,[Text.UTF8Encoding]::new($false))
    $unchanged=$before -ceq $after
    $reportPath=Join-Path $root 'planting-network-audit.json'
    $report=if(Test-Path -LiteralPath $reportPath){Get-Content -Raw -Encoding UTF8 -LiteralPath $reportPath | ConvertFrom-Json}else{$null}
    $success=$job.ExitCode -eq 0 -and $report -and $report.failures -eq 0 -and $unchanged
    [IO.File]::WriteAllText((Join-Path $root 'status.json'),(@{exitCode=$job.ExitCode;success=$success;production_saves_unchanged=$unchanged;root=$root;checks=$report.checks;failures=$report.failures;network_transport_exercised=$false}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Write-Output ('Exit='+$job.ExitCode+' checks='+$report.checks+' failures='+$report.failures+' production_saves_unchanged='+$unchanged)
    if(-not $success){exit 1}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}