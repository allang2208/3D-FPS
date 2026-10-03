param([int]$QueueSeconds=1200,[switch]$SkipAssetProduction)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=$PSScriptRoot
$engineRoot='E:\Program Files (x86)\UE_5.8\Engine'
$deadline=(Get-Date).AddSeconds($QueueSeconds)
$dll=Join-Path $projectRoot 'Binaries\Win64\UnrealEditor-FPSGAME.dll'
function Editor-OwnsProject {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
        Where-Object {$_.CommandLine -like '*FPSGAME\FPSGAME.uproject*'}).Count -gt 0
}
function Native-BuildActive {
    @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" |
        Where-Object {$_.CommandLine -match 'UnrealBuildTool'}).Count -gt 0
}
function Dll-Available {
    if(-not (Test-Path -LiteralPath $dll)){return $true}
    try {$handle=[IO.File]::Open($dll,'Open','ReadWrite','None');$handle.Dispose();return $true}
    catch {return $false}
}
Write-Output 'Waiting outside the asset mutex for native build and editor DLL access.'
while((Editor-OwnsProject) -or (Native-BuildActive) -or -not (Dll-Available)) {
    if((Get-Date) -gt $deadline){throw 'Source and production inputs preserved; editor/build access still occupied.'}
    Start-Sleep -Seconds 5
}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$assetLog=Join-Path $out ('asset-commandlet-'+$stamp+'.log')
$assetConsole=Join-Path $out ('asset-console-'+$stamp+'.txt')
$assetReceipt=Join-Path $out 'asset_installation.json'
$assetExit=0
if (-not $SkipAssetProduction) {
    $mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $acquired=$false
    try {
        try {$acquired=$mutex.WaitOne(45000)} catch [Threading.AbandonedMutexException] {$acquired=$true}
        if(-not $acquired){throw 'Asset batch mutex remains occupied; no additional editor was started.'}
        if((Editor-OwnsProject) -or -not (Dll-Available)){throw 'Editor reopened; preserve its loaded assets.'}
        Write-Output 'Producing world-space wake smoke and in-smoke screen blur with a headless commandlet.'
        $assetStarted=Get-Date
        $assetArguments=@((Join-Path $projectRoot 'FPSGAME.uproject'),'-run=pythonscript',
            ('-script='+$out+'\author_world_smoke.py'),'-unattended','-NullRHI','-nosplash',
            '-NoSound','-NoCrashDialog','-stdout','-FullStdOutLogOutput',('-abslog='+$assetLog))
        & (Join-Path $engineRoot 'Binaries\Win64\UnrealEditor-Cmd.exe') @assetArguments *> $assetConsole
        $assetExit=$LASTEXITCODE
        if(-not (Test-Path -LiteralPath $assetReceipt) -or (Get-Item -LiteralPath $assetReceipt).LastWriteTime -lt $assetStarted){
            Get-Content -LiteralPath $assetConsole -Tail 45;throw ('World smoke saves incomplete: '+$assetExit)
        }
    } finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose()}
}
if(-not (Test-Path -LiteralPath $assetReceipt)){throw 'No completed asset save receipt; native build deferred.'}
$assets=Get-Content -LiteralPath $assetReceipt -Raw | ConvertFrom-Json
if(@($assets.saved_assets).Count -ne 2){throw 'The two new assets were not both saved.'}
Write-Output ('World smoke asset saves complete. Commandlet exit: '+$assetExit)
while((Native-BuildActive) -or -not (Dll-Available)) {
    if((Get-Date) -gt $deadline){throw 'Assets saved; native build access remains occupied.'}
    Start-Sleep -Seconds 5
}
$log=Join-Path $projectRoot ('Saved\BuildEditor\slag-world-smoke-v19-'+$stamp+'.log')
$console=Join-Path $out ('build-console-'+$stamp+'.txt')
Write-Output 'Building FPSGAMEEditor gameplay module with regular UHT and C++ compilation.'
$buildArguments=@('FPSGAMEEditor','Win64','Development',('-project='+$projectRoot+'\FPSGAME.uproject'),
    '-NoHotReloadFromIDE','-MaxParallelActions=2',('-Log='+$log),'-Module=FPSGAME')
& (Join-Path $engineRoot 'Build\BatchFiles\Build.bat') @buildArguments *> $console
$result=$LASTEXITCODE
if($result -ne 0){Get-Content -LiteralPath $console -Tail 55;throw ('Editor build failed: '+$result)}
$product=Get-Item -LiteralPath $dll
@{revision='WorldSmokeV19';target='FPSGAMEEditor';exit_code=$result;log=$log;console=$console;
  asset_commandlet_log=$assetLog;asset_commandlet_exit=$assetExit;asset_production_skipped=[bool]$SkipAssetProduction;
  asset_receipt=$assetReceipt;world_space_smoke=$true;in_smoke_only=$true;clear_on_exit=$true;
  dll=$product.FullName;dll_bytes=$product.Length;dll_written_utc=$product.LastWriteTimeUtc.ToString('o');
  regular_base_dll_build=$true;gameplay_module_only=$true;full_editor_target_built=$false;
  game_executable_built=$false;runtime_tested=$false;interactive_editor_started=$false} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'build_installation.json') -Encoding utf8
Write-Output ('SLAG_V19_ASSETS_AND_EDITOR_MODULE_SAVED '+$log)
