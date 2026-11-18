param([Parameter(Mandatory=$true)][string]$HostProject)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $project 'SourceAssets/HillsClosure20261118/BeechMaterial'
New-Item -ItemType Directory -Force -Path $out|Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'An editor is active; preserve loaded assets.'}
    $hostFile=(Resolve-Path -LiteralPath $HostProject).Path
    $arguments=@(('"'+$hostFile+'"'),'-run=pythonscript',('-script="'+$PSScriptRoot+'/repair_hills_beech_material.py"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-UserDir="'+(Split-Path (Split-Path $hostFile))+'"'),('-abslog="'+$out+'/repair.log"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $peerHandle=$p.Handle;$p.WaitForExit()
    @{exit_code=$p.ExitCode;finished=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$out/exit.json" -Encoding utf8
    if($p.ExitCode -ne 0){throw 'Beech material repair failed'}
    Get-Content -LiteralPath "$out/saved.json" -Raw
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
