param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Label)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$output = Join-Path $projectRoot 'SourceAssets/ModernTacticalSet20261113/ShoulderFit20261118'
$stage = Join-Path $output 'PythonHost'
$stageContent = Join-Path $stage 'Content'
$project = Join-Path $stage 'TS01Shoulders.uproject'
New-Item -ItemType Directory -Force -Path $stageContent | Out-Null
if (!(Test-Path -LiteralPath $project)) {
    Copy-Item -LiteralPath (Join-Path $output '../CombatShirtR4/StageHostLean/TS01CombatR4.uproject') -Destination $project
}
foreach ($name in @('AsianMale_Jason','Characters','Items','Weapons')) {
    $link = Join-Path $stageContent $name
    $target = (Resolve-Path (Join-Path $projectRoot ('Content/'+$name))).Path
    if (!(Test-Path -LiteralPath $link)) {
        New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    }
    if ((Get-Item -LiteralPath $link).Target -ne $target) { throw "Unexpected content mount at $link" }
}
$log = Join-Path $output ($Label+'-'+(Get-Date -Format 'HHmmss-fff')+'.log')
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    & $engine $project '/Engine/Maps/Entry' '-run=pythonscript' "-script=$Script" '-unattended' '-nop4' '-nosound' '-nosplash' '-NullRHI' '-Multiprocess' '-AssetGatherAll=false' '-asyncskinnedassetcompilation=0' '-asyncstaticmeshcompilation=0' '-asynctexturecompilation=0' "-abslog=$log" *> "$log.stdout"
    if ($LASTEXITCODE -ne 0) { throw "Stage $Label returned $LASTEXITCODE, see $log" }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
