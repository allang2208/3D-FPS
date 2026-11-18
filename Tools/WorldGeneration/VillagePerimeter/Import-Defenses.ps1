$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$out=Join-Path $project 'SourceAssets/VillageDefenses20261117'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    while($true) {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $busy.Count){break}
        Write-Output 'Waiting for the active engine/build process; no process will be stopped.'
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    New-Item -ItemType Directory -Force -Path "$out/Logs" | Out-Null
    $arguments=@(('"'+$project+'/FPSGAME.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$project+'/Tools/WorldGeneration/VillagePerimeter/import_defenses.py"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-AssetGatherAll=false',
        '-NoAssetRegistryCacheWrite',('-abslog="'+$out+'/Logs/import-engine.log"'))
    $previousSdk=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$out/Logs/import-stdout.log" -RedirectStandardError "$out/Logs/import-stderr.log"
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$previousSdk}
    @{exit_code=$process.ExitCode;finished=(Get-Date).ToString('o');gameplay_started=$false;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out/import-process.json" -Encoding utf8
    if($process.ExitCode -ne 0){exit $process.ExitCode}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
