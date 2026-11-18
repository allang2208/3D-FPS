param([Parameter(Mandatory=$true)][string]$HostProject)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$out=Join-Path $project 'SourceAssets/HillsLandscapeRepair20261117/SolidScansR9'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'An editor is active; use its MCP batch for the data asset.'}
    $hostFile=(Resolve-Path -LiteralPath $HostProject).Path
    $arguments=@(('"'+$hostFile+'"'),'-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/import_solid_scans.py"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess',
        '-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-UserDir="'+(Split-Path (Split-Path $hostFile))+'"'),('-abslog="'+$out+'/import.log"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $process.WaitForExit()
    @{exit_code=$process.ExitCode;finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$out/exit.json" -Encoding utf8
    if($process.ExitCode -ne 0){throw 'Solid scan import failed'}
    Get-Content -LiteralPath "$out/saved.json" -Raw
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
