param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$stage = Join-Path $project 'Saved/VillageCarpenter/GroundDeck'
$hostDir = Join-Path $stage 'Host'
New-Item -ItemType Directory -Force -Path $hostDir | Out-Null
$hostProject = Join-Path $hostDir 'GroundDeck.uproject'
@{
    FileVersion = 3
    EngineAssociation = '5.8'
    Plugins = @('PythonScriptPlugin','EditorScriptingUtilities','GeometryScripting') | ForEach-Object { @{Name=$_;Enabled=$true} }
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $hostProject -Encoding utf8
if (-not (Test-Path "$hostDir/Content")) {
    New-Item -ItemType Junction -Path "$hostDir/Content" -Target "$project/Content" | Out-Null
}
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $log = Join-Path $stage ('deck-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    $argsList = @(('"'+$hostProject+'"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/author_ground_deck.py"'),'-unattended','-nop4','-nosplash','-nosound',
        '-NullRHI','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',('-abslog="'+$log+'"'))
    $exe = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $job = Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $null = $job.Handle
    $job.WaitForExit()
    $job.Refresh()
    if ($job.ExitCode -ne 0) {throw "Ground deck authoring failed. See $log"}
} finally {
    if ($held) {$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
