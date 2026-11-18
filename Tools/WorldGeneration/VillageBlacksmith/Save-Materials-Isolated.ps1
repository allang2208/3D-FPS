# Material-only authoring host: shares Content but does not load FPSGAME game DLLs.
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$out=Join-Path $project 'SourceAssets/HillsVillageBlacksmith20261117'
$hostRoot=Join-Path $project 'Saved/HillsVillageBlacksmithMaterialHost20261117'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $editors=@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue)
    if($editors.Count){throw 'An editor is running; preserve loaded assets and use its existing bridge.'}
    New-Item -ItemType Directory -Force -Path $hostRoot | Out-Null
    $content=Join-Path $hostRoot 'Content'
    if(-not(Test-Path -LiteralPath $content)){
        New-Item -ItemType Junction -Path $content -Target (Join-Path $project 'Content') | Out-Null
    }
    $descriptor=[ordered]@{FileVersion=3;EngineAssociation='5.8';Category='';Description='Isolated village material authoring';Plugins=@(
        @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})}
    $hostProject=Join-Path $hostRoot 'HillsMaterialAuthor.uproject'
    [IO.File]::WriteAllText($hostProject,($descriptor|ConvertTo-Json -Depth 4),[Text.UTF8Encoding]::new($false))
    $arguments=@(('"'+$hostProject+'"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/save_furniture_usage.py"'),'-unattended','-nop4','-nosplash','-nosound',
        '-NullRHI','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-abslog="'+$out+'/Logs/material-usage-isolated-engine.log"'))
    $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/Logs/material-usage-isolated-stdout.log" -RedirectStandardError "$out/Logs/material-usage-isolated-stderr.log"
    $null=$process.Handle
    $process.WaitForExit()
    if($null -eq $process.ExitCode){throw 'Commandlet exit code unavailable; retain the engine log and asset-save receipt.'}
    @{exit_code=$process.ExitCode;finished=(Get-Date).ToString('o');isolated_material_host=$true;host_declares_game_modules=$false;gameplay_started=$false;rendered=$false}|
        ConvertTo-Json|Set-Content -LiteralPath "$out/material-usage-isolated-process.json" -Encoding utf8
    if($process.ExitCode -ne 0){exit $process.ExitCode}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
