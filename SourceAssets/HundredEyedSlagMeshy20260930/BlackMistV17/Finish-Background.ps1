param([int]$QueueSeconds=600)
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
Write-Output 'Waiting for the user to save/close FPSGAME and for native build access.'
while((Editor-OwnsProject) -or (Native-BuildActive) -or -not (Dll-Available)) {
    if((Get-Date) -gt $deadline){throw 'Source and asset inputs preserved; editor/build access still occupied.'}
    Start-Sleep -Seconds 5
}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$assetLog=Join-Path $out ('asset-commandlet-'+$stamp+'.log')
$assetConsole=Join-Path $out ('asset-console-'+$stamp+'.txt')
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$acquired=$false
try {
    try {$acquired=$mutex.WaitOne(45000)} catch [Threading.AbandonedMutexException] {$acquired=$true}
    if(-not $acquired){throw 'Asset batch mutex remains occupied; no second editor was started.'}
    # Recheck while holding the existing batch lock before loading shared packages.
    if((Editor-OwnsProject) -or -not (Dll-Available)){throw 'Editor reopened; preserve its loaded/unsaved assets.'}
    Write-Output 'Producing and saving the three black mist assets with a headless Python commandlet.'
    $assetArguments=@((Join-Path $projectRoot 'FPSGAME.uproject'),'-run=pythonscript',
        ('-script='+$out+'\author_black_mist.py'),'-unattended','-NullRHI','-nosplash',
        '-NoSound','-NoCrashDialog','-stdout','-FullStdOutLogOutput',('-abslog='+$assetLog))
    & (Join-Path $engineRoot 'Binaries\Win64\UnrealEditor-Cmd.exe') @assetArguments *> $assetConsole
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $assetConsole -Tail 45;throw 'Black mist production commandlet failed.'}
} finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose()}
$assetReceipt=Join-Path $out 'asset_installation.json'
if(-not (Test-Path -LiteralPath $assetReceipt)){throw 'No completed asset save receipt; native build deferred.'}
$log=Join-Path $projectRoot ('Saved\BuildEditor\slag-black-mist-v17-'+$stamp+'.log')
$console=Join-Path $out ('build-console-'+$stamp+'.txt')
Write-Output 'Building the FPSGAMEEditor gameplay module through regular UHT and C++ compilation.'
$buildArguments=@('FPSGAMEEditor','Win64','Development',('-project='+$projectRoot+'\FPSGAME.uproject'),
    '-NoHotReloadFromIDE','-WaitMutex','-MaxParallelActions=2',('-Log='+$log),'-Module=FPSGAME')
& (Join-Path $engineRoot 'Build\BatchFiles\Build.bat') @buildArguments *> $console
$result=$LASTEXITCODE
if($result -ne 0){Get-Content -LiteralPath $console -Tail 55;throw ('Editor build failed: '+$result)}
$product=Get-Item -LiteralPath $dll
@{revision='BlackMistV17';target='FPSGAMEEditor';exit_code=$result;log=$log;console=$console;
  asset_commandlet_log=$assetLog;asset_receipt=$assetReceipt;included_ragdoll_revision='RagdollGroundV16';
  dll=$product.FullName;dll_bytes=$product.Length;dll_written_utc=$product.LastWriteTimeUtc.ToString('o');
  regular_base_dll_build=$true;gameplay_module_only=$true;full_editor_target_built=$false;
  game_executable_built=$false;runtime_tested=$false;interactive_editor_started=$false} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'build_installation.json') -Encoding utf8
Write-Output ('SLAG_V17_ASSETS_AND_EDITOR_MODULE_SAVED '+$log)
