param([Parameter(Mandatory=$true)][string]$HostProject)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$out=Join-Path $project 'SourceAssets/HillsLandscapeRepair20261117/MaterialsR7'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Use the existing editor MCP batch for loaded materials.'}
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $hostFile=(Resolve-Path -LiteralPath $HostProject).Path
    $userDir=Split-Path (Split-Path $hostFile)
    $arguments=@(('"'+$hostFile+'"'),'-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/repair_limestone_materials.py"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess',
        '-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-UserDir="'+$userDir+'"'),('-abslog="'+$out+'/repair.log"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    @{exit_code=$p.ExitCode;finished=(Get-Date).ToString('o')} | ConvertTo-Json |
        Set-Content -LiteralPath "$out/exit.json" -Encoding utf8
    if($p.ExitCode -ne 0){throw 'Limestone material commandlet failed'}
    Get-Content -LiteralPath "$out/saved.json" -Raw
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
