param()
$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$project='D:/FPS3D/ThunderHammerFullReviewHost20261102'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied.'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.ThreadCount -gt 0) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    if($busy.Count){throw 'Existing runtime/build preserved; package not started.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -MaxParallelActions=4 "-Log=$PSScriptRoot/production-FPSGAME.log" *> "$PSScriptRoot/production-FPSGAME-console.log"
    $code=$LASTEXITCODE
    @{target='FPSGAME';exit_code=$code;completed=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content "$PSScriptRoot/build-FPSGAME.json" -Encoding utf8
    if($code -ne 0){throw 'Game build failed.'}
    foreach($name in @('FPSGAME.exe','FPSGAME.target')){Copy-Item -LiteralPath "D:/FPS3D/FPSGAME/Binaries/Win64/$name" -Destination "$project/Binaries/Win64/$name" -Force}
    & python "$PSScriptRoot/prepare_package.py"
    if($LASTEXITCODE -ne 0){throw 'Package scope preparation failed.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/RunUAT.bat' BuildCookRun "-project=$project/FPSGAME.uproject" -noP4 -utf8output -platform=Win64 -targetplatform=Win64 -clientconfig=Development -nocompileeditor -noprereqs -skipbuild -cook '-map=/Engine/Maps/Entry' -stage -pak -iostore -nodebuginfo -archive "-archivedirectory=$PSScriptRoot/Package" '-AdditionalCookerOptions=-unattended -nullrhi -nosound -NoLiveCoding -AssetGatherAll=false -asyncassetcompilationmaxconcurrency=2 -asyncskinnedassetcompilation=0 -ini:Editor:[CookSettings]:PackagesPerGC=100,[CookSettings]:MemoryMinFreePhysical=4096,[CookSettings]:MemoryMinFreeVirtual=8192,[CookSettings]:MaxConcurrentShaderJobs=16,[CookPlatformDataCacheSettings]:SkeletalMesh=4,[CookPlatformDataCacheSettings]:StaticMesh=8,[CookPlatformDataCacheSettings]:Texture2D=32' *> "$PSScriptRoot/package-console.log"
    $code=$LASTEXITCODE
    @{scope='hammer scenario Development cook/stage/archive';exit_code=$code;completed=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content "$PSScriptRoot/package-receipt.json" -Encoding utf8
    Write-Output "THUNDER_PACKAGE_EXIT=$code";exit $code
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
