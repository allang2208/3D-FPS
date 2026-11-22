param([string]$Engine='E:/Program Files (x86)/UE_5.8',[string[]]$Parts=@(),[switch]$Masonry)
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath "$PSScriptRoot/../../..").Path
$root='F:/FPSGAMEData/ArtProduction/HillsVillageBakery'
$run=Join-Path $root ('Architecture-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path "$run/Config" -Force | Out-Null
New-Item -ItemType Junction -Path "$run/Content" -Target "$project/Content" | Out-Null
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},
    @{Name='GeometryScripting';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$run/BakeryAuthor.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') |
    Set-Content -LiteralPath "$run/Config/DefaultEngine.ini" -Encoding utf8
$env:BAKERY_ARCHITECTURE_RECEIPT="$run/saved.json"
$env:BAKERY_ARCHITECTURE_PARTS=$Parts -join ','
$cache='F:/FPSGAMEData/Caches/DerivedDataCache'
$author=if ($Masonry){'author_bakery_masonry.py'}else{'author_architecture.py'}
$argsList=@(('"'+$run+'/BakeryAuthor.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
    ('-script="'+$PSScriptRoot+'/'+$author+'"'),'-nullrhi','-unattended','-nosplash','-nosound',
    '-nop4','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
    ('-LocalDataCachePath='+$cache),('-ZenDataPath='+$cache+'/Zen'),
    ('-ini:Engine:[VirtualTextureChunkDDCCache]:Path='+$cache+'/VT'),('-abslog="'+$run+'/author.log"'))
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mutex.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $proc=Start-Process "$Engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" -ArgumentList $argsList -WindowStyle Hidden -PassThru -Wait
    if ($proc.ExitCode -ne 0 -or -not (Test-Path -LiteralPath "$run/saved.json")){
        Select-String -Path "$run/author.log" -Pattern 'Traceback|LogPython: Error|Fatal error|BAKERY_ARCHITECTURE' | Select-Object -Last 19
        throw "Bakery authoring did not finish. See $run/author.log"
    }
    Write-Output "Saved bakery architecture. $run/saved.json"
} finally {if ($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
