$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $project 'SourceAssets/HillsHilltopVillage20261117'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    foreach($target in @('FPSGAMEEditor','FPSGAME')) {
        $receipt=Get-Content -LiteralPath "$out/$target-build.json" -Raw | ConvertFrom-Json
        if($receipt.exit_code -ne 0){throw "The $target build is incomplete; current world retained."}
    }
    while($true) {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $busy.Count){break}
        Write-Output 'Waiting for the active engine/build process; current world retained.'
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $arguments=@(('"'+$project+'/FPSGAME.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$project+'/Tools/WorldGeneration/upgrade_hills_hilltop.py"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-AssetGatherAll=false',
        '-NoAssetRegistryCacheWrite',('-abslog="'+$out+'/Logs/world-migration-engine.log"'))
    $previousSdk=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$out/Logs/world-migration-stdout.log" -RedirectStandardError "$out/Logs/world-migration-stderr.log"
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$previousSdk}
    @{exit_code=$process.ExitCode;finished=(Get-Date).ToString('o');gameplay_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out/world-migration-process.json" -Encoding utf8
    if($process.ExitCode -ne 0){exit $process.ExitCode}
    Get-Content -LiteralPath "$out/world-migration.json"
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
