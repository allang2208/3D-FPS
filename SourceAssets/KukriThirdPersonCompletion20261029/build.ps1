param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$build='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$receipt=Join-Path $PSScriptRoot 'build.json'
$results=@()
foreach($target in $Targets){
    $deadline=(Get-Date).AddMinutes(15)
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -match '^(cl|link)\.exe$' -and $_.CommandLine -match 'FPSGAME')
        })
        if($busy.Count -eq 0){break}
        if((Get-Date) -gt $deadline){throw 'Another build is still active; preserved its process.'}
        Start-Sleep -Seconds 10
    } while($true)
    if($target -eq 'FPSGAMEEditor'){
        $dll=Join-Path $project 'Binaries\Win64\UnrealEditor-FPSGAME.dll'
        $dllDeadline=(Get-Date).AddMinutes(15)
        $reported=$false
        while(Test-Path -LiteralPath $dll){
            try {$handle=[IO.File]::Open($dll,'Open','ReadWrite','None');$handle.Dispose();break}
            catch [IO.IOException] {
                if((Get-Date) -gt $dllDeadline){throw 'Editor DLL remains in use; preserved the running process.'}
                if(-not $reported){Write-Output 'Waiting for the existing Editor DLL reader to finish.';$reported=$true}
                Start-Sleep -Seconds 10
            }
        }
    }
    $log=Join-Path $PSScriptRoot "$target-build.log"
    $console=Join-Path $PSScriptRoot "$target-console.log"
    if(Get-Process UnrealEditor,FPSGAME -ErrorAction SilentlyContinue){throw "An editor or game is active; build preserved the running process."}
    Write-Output "Building $target"
    & $build $target Win64 Development "-Project=$project\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 "-Log=$log" *> $console
    $code=$LASTEXITCODE
    $results+=@{target=$target;exit_code=$code;completed=(Get-Date).ToString('o');log=$log}
    @{builds=$results;tests_run=$false;editor_started=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receipt -Encoding utf8
    Get-Content -LiteralPath $console -Tail 12
    if($code -ne 0){exit $code}
}
