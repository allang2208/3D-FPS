$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME/FPSGAME.uproject'
$results=@()
foreach($target in @('FPSGAMEEditor','FPSGAME')) {
    while($active=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat') })) {
        Write-Output ('Waiting for active build PID '+($active.ProcessId -join ','))
        foreach($p in $active){Wait-Process -Id $p.ProcessId -ErrorAction SilentlyContinue}
    }
    while($active=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*FPSGAME*' })) {
        Write-Output ('Waiting for project commandlet PID '+($active.ProcessId -join ','))
        foreach($p in $active){Wait-Process -Id $p.ProcessId -ErrorAction SilentlyContinue}
    }
    if(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -like '*FPSGAME*' }) {
        throw 'Project editor/commandlet is running; preserve it before native link.'
    }
    $log=Join-Path $PSScriptRoot ('build-'+$target+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development ('-Project='+$project) -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=6 *> $log
    $code=$LASTEXITCODE
    $results+=@{target=$target;exit_code=$code;log=$log;finished=(Get-Date).ToString('s')}
    @{targets=$results} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
    Write-Output ($target+' exit='+$code);Get-Content -LiteralPath $log -Tail 15
    if($code -ne 0){exit $code}
}
