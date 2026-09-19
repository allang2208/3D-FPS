$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$stockRoot=Join-Path $taskRoot 'TacticalTelescopic'
$blender='E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$python='E:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe'
$editor='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$importHost='D:\FPS3D\FPSGAME\SourceAssets\ReferenceSkeletonStock5080_20260913\Refined\ImportHost\StockAssetImport.uproject'
foreach($stage in @('author_game_body','author_variants')) {
    & $blender --background --python-exit-code 1 --python (Join-Path $stockRoot ($stage+'.py')) *> (Join-Path $stockRoot ($stage+'.log'))
    if($LASTEXITCODE -ne 0){throw "Authoring failed: $stage"}
    Write-Output "Completed $stage"
}
& $blender --background --python-exit-code 1 --python (Join-Path $taskRoot 'render_stock_icons.py') -- tactical_telescopic *> (Join-Path $taskRoot 'render_tactical_icon.log')
if($LASTEXITCODE -ne 0){throw 'Tactical icon render failed'}
& $python (Join-Path $taskRoot 'install_icons.py')
if($LASTEXITCODE -ne 0){throw 'Icon install failed'}
foreach($scriptPath in @((Join-Path $stockRoot 'import_assets.py'),(Join-Path $taskRoot 'import_icons.py'))) {
    $jobParent=Split-Path -Parent $scriptPath
    $jobName=[IO.Path]::GetFileNameWithoutExtension($scriptPath)
    & $editor $importHost -run=pythonscript "-script=$scriptPath" -multiprocess -ddc=InstalledNoZenLocalFallback -unattended -nosplash -NullRHI -nosound "-abslog=$(Join-Path $jobParent ($jobName+'.log'))" *> (Join-Path $jobParent ($jobName+'_console.log'))
    if($LASTEXITCODE -ne 0){throw "Import failed: $jobName"}
    Write-Output "Completed $jobName"
}
& $blender --background --python-exit-code 1 --python (Join-Path $taskRoot 'render_lineup.py') *> (Join-Path $taskRoot 'render_lineup.log')
if($LASTEXITCODE -ne 0){throw 'Lineup render failed'}
Write-Output 'Stock asset delivery complete. Gameplay testing remains manual.'
