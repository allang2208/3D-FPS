param([ValidateSet('Build','Import','Publish')][string]$Stage='Build')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$sourceRoot=Join-Path $projectRoot 'SourceAssets/ChainmailSharedSway20260929'
if ($Stage -eq 'Build') {
    & (Join-Path $projectRoot 'Tools/Build/Build-Editor.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Shared sway native build failed.' }
    $modulePath=Join-Path $projectRoot 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
    $record=@{
        complete=$true; target='FPSGAMEEditor Win64 Development'; module=$modulePath
        module_written_utc=(Get-Item -LiteralPath $modulePath).LastWriteTimeUtc.ToString('o')
        completed_utc=[DateTime]::UtcNow.ToString('o'); runtime_tested=$false
        source_hashes=@{}
    }
    foreach($name in @('FPSOutfitSecondaryMotion.h','FPSOutfitSecondaryMotion.cpp','FPSModularOutfitComponent.cpp')) {
        $record.source_hashes[$name]=(Get-FileHash -LiteralPath (Join-Path $projectRoot ('Source/FPSGAME/Characters/'+$name)) -Algorithm SHA256).Hash
    }
    $record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $sourceRoot 'native-build.json') -Encoding UTF8
} elseif($Stage -eq 'Import') {
    & (Join-Path $projectRoot 'Tools/ModularOutfit/Run-Authoring.ps1') -Script Tools/ModularOutfit/import_chainmail_shared_sway.py -Log Saved/chainmail-shared-sway-import-20260929.log
} else {
    & py -3.11 (Join-Path $projectRoot 'Tools/ModularOutfit/publish_chainmail_shared_sway.py')
    if ($LASTEXITCODE -ne 0) { throw 'Shared sway recipe publication stopped.' }
}
