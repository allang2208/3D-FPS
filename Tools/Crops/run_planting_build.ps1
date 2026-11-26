param([ValidateSet('Editor','Game')][string]$Target='Editor')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new()
$projectRoot='D:\FPS3D\FPSGAME'
$receiptRoot=Join-Path $projectRoot 'SourceAssets\PlantingGameplay20261022'
$engineRoot='E:\Program Files (x86)\UE_5.8'
$buildTarget=if($Target -eq 'Editor'){'FPSGAMEEditor'}else{'FPSGAME'}
$statePath=Join-Path $receiptRoot ('build-'+$Target.ToLower()+'-status.json')
$deadline=[DateTime]::UtcNow.AddMinutes(45)
function Write-State([string]$State){[IO.File]::WriteAllText($statePath,(@{state=$State;target=$buildTarget;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))}
function Output-Free([string]$Path){
    if(-not(Test-Path -LiteralPath $Path)){return $true}
    try{$stream=[IO.File]::Open($Path,'Open','ReadWrite','None');$stream.Dispose();return $true}catch{return $false}
}
Write-State 'waiting_for_existing_builds'
$announced=$false
while($true){
    $busy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','link.exe')
    })
    $output=Join-Path $projectRoot $(if($Target -eq 'Editor'){'Binaries\Win64\UnrealEditor-FPSGAME.dll'}else{'Binaries\Win64\FPSGAME.exe'})
    if($busy.Count -eq 0 -and (Output-Free $output)){break}
    if(-not $announced){Write-Output 'Waiting for existing compiler/linker jobs and loaded target binaries; no build launched.';$announced=$true}
    if([DateTime]::UtcNow -ge $deadline){Write-State 'blocked_by_existing_build_or_binary_lock';exit 75}
    Start-Sleep -Seconds 10
}
Write-State 'building'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$log=Join-Path $receiptRoot ('build-'+$Target.ToLower()+'-'+$stamp+'.log')
$arguments=@($buildTarget,'Win64','Development',('-Project='+(Join-Path $projectRoot 'FPSGAME.uproject')),
    '-NoHotReload','-NoHotReloadFromIDE','-NoUBTMakefiles','-NoUBA','-MaxParallelActions=4',('-Log='+$log))
Write-Output ('Building '+$buildTarget+'; log '+$log)
& (Join-Path $engineRoot 'Engine\Build\BatchFiles\Build.bat') @arguments *> ($log+'.console.txt')
$result=$LASTEXITCODE
$ok=$result -eq 0 -and (Select-String -LiteralPath $log -Pattern '^Result: Succeeded' -Quiet)
[IO.File]::WriteAllText($statePath,(@{state=$(if($ok){'succeeded'}else{'failed'});target=$buildTarget;exitCode=$result;log=$log;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
Write-Output ('Build '+$buildTarget+' exit '+$result)
Get-Content -LiteralPath $log -Tail 12
if(-not $ok){exit 1}
