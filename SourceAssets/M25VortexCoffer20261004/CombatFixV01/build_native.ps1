param([int]$MaximumWaitSeconds=600)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$recordRoot=Join-Path $PSScriptRoot 'Records'
$buildTool='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
foreach($targetName in @('FPSGAME','FPSGAMEEditor')) {
    $deadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
    $announced=$false
    while($true) {
        $processes=Get-CimInstance Win32_Process
        $activeBuilds=@($processes | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe')
        })
        $owners=@($processes | Where-Object {
            ($targetName -eq 'FPSGAMEEditor' -and $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME') -or
            ($targetName -eq 'FPSGAME' -and $_.Name -eq 'FPSGAME.exe')
        })
        if($activeBuilds.Count -eq 0 -and $owners.Count -eq 0){break}
        if(-not $announced){Write-Output ('M25_BUILD_WAIT '+$targetName);$announced=$true}
        if([DateTime]::UtcNow -ge $deadline){Write-Output ('M25_BUILD_DEFERRED '+$targetName);exit 75}
        Start-Sleep -Seconds 10
    }
    # Keep the existing target's Live Coding mode to avoid an unrelated full rebuild.
    $modeArgs=@()
    $definitions=Join-Path $projectRoot ('Intermediate/Build/Win64/x64/'+$targetName+'/Development/Core/SharedDefinitions.Core.Cpp20.h')
    if((Test-Path -LiteralPath $definitions) -and [IO.File]::ReadAllText($definitions) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$modeArgs+='-NoLiveCoding'}
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $log=Join-Path $recordRoot ('build_'+$targetName+'_'+$stamp+'.log')
    Write-Output ('M25_BUILD_START '+$targetName+' '+$log)
    & $buildTool $targetName Win64 Development ('-Project='+$projectRoot+'/FPSGAME.uproject') -NoHotReload -NoHotReloadFromIDE @modeArgs -MaxParallelActions=4 ('-Log='+$log) *> ($log+'.stdout')
    $result=$LASTEXITCODE
    [ordered]@{target=$targetName;exit_code=$result;log=$log;finished_at=(Get-Date -Format o);tested=$false} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $recordRoot ('build_'+$targetName+'.json')) -Encoding UTF8
    Write-Output ('M25_BUILD_RESULT '+$targetName+' '+$result)
    if($result -ne 0){exit $result}
}
