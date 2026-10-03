param([int]$QueueSeconds=3600,[switch]$GameplayModuleOnly)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$out=$PSScriptRoot
$deadline=(Get-Date).AddSeconds($QueueSeconds)
$dll=Join-Path $projectRoot 'Binaries\Win64\UnrealEditor-FPSGAME.dll'
function Test-BuildActive {
    @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}).Count -gt 0
}
function Test-DllAvailable {
    if(-not (Test-Path -LiteralPath $dll)){return $true}
    try {$handle=[IO.File]::Open($dll,'Open','ReadWrite','None');$handle.Dispose();return $true}
    catch {return $false}
}
Write-Output 'Waiting outside the asset mutex for native builds and editor DLL access.'
while((Test-BuildActive) -or -not (Test-DllAvailable)) {
    if((Get-Date) -gt $deadline){throw 'Build access still occupied; source and animation assets preserved.'}
    Start-Sleep -Seconds 5
}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$log=Join-Path $projectRoot ('Saved\BuildEditor\slag-ragdoll-ground-v16-'+$stamp+'.log')
$console=Join-Path $out ('build-console-'+$stamp+'.txt')
Write-Output 'Building FPSGAMEEditor with the regular header dependency and reflection pipeline.'
$buildArguments=@('FPSGAMEEditor','Win64','Development',('-project='+$projectRoot+'\FPSGAME.uproject'),'-NoHotReloadFromIDE','-MaxParallelActions=2',('-Log='+$log))
if ($GameplayModuleOnly) { $buildArguments+='-Module=FPSGAME' }
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' @buildArguments *> $console
$result=$LASTEXITCODE
if($result -ne 0) {Get-Content -LiteralPath $console -Tail 45;throw ('Editor build failed: '+$result)}
$product=Get-Item -LiteralPath $dll
@{revision='RagdollGroundV16';target='FPSGAMEEditor';exit_code=$result;log=$log;console=$console;
  dll=$product.FullName;dll_bytes=$product.Length;dll_written_utc=$product.LastWriteTimeUtc.ToString('o');
  regular_base_dll_build=$true;gameplay_module_only=[bool]$GameplayModuleOnly;full_editor_target_built=(-not [bool]$GameplayModuleOnly);game_executable_built=$false;runtime_tested=$false;editor_started=$false} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'build_installation.json') -Encoding utf8
Write-Output ('SLAG_V16_EDITOR_BUILD_COMPLETE '+$log)
