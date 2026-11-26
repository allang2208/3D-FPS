$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$sets=Join-Path $projectRoot 'SourceAssets/ModernTacticalSet20261113'
$revision=Join-Path $sets 'HelmetNapeR3'
$stageRoot=Join-Path $revision 'StageHost'
$materialParent='Content/Characters/ModularOutfit20260924/ModernTacticalSet20261113'
$stageParent=Join-Path $stageRoot $materialParent
New-Item -ItemType Directory -Force -Path $stageParent | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stageRoot 'Config') | Out-Null
$stageProject=Join-Path $stageRoot 'HelmetNapeHost.uproject'
Copy-Item -LiteralPath (Join-Path $sets 'HelmetContourR2/StageHost/HelmetContourHost.uproject') -Destination $stageProject
Copy-Item -LiteralPath (Join-Path $sets 'HelmetContourR2/StageHost/Config/DefaultEngine.ini') -Destination (Join-Path $stageRoot 'Config/DefaultEngine.ini')
$link=Join-Path $stageParent 'HelmetDetailR1'
$target=(Resolve-Path (Join-Path $projectRoot "$materialParent/HelmetDetailR1")).Path
if (-not (Test-Path -LiteralPath $link)) {
    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
}
if ((Get-Item -LiteralPath $link).Target -ne $target) {throw "Unexpected material mount $link"}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$log=Join-Path $revision "save-$stamp.log"
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $engine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $command=Join-Path $PSScriptRoot 'helmet_nape_save.py'
    & $engine $stageProject '/Engine/Maps/Entry' '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-Multiprocess' '-NoAssetRegistryCache' '-AssetGatherAll=false' '-asyncstaticmeshcompilation=0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen' "-abslog=$log" '-run=pythonscript' "-script=$command" *> "$log.stdout"
    if ($LASTEXITCODE) {throw "Helmet save exited $LASTEXITCODE; see $log"}
} finally {
    if ($held) {$gate.ReleaseMutex()}
    $gate.Dispose()
}
