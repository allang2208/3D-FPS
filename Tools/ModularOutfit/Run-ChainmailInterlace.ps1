param([string]$ScriptPath='D:/FPS3D/FPSGAME/SourceAssets/ChainmailInterlace20260929/Integration/offline.py')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
# Future reimports use the shared background-authoring guard. If an editor has
# loaded this now-published family, use the existing bridge's short batches.
& "$projectRoot/Tools/ModularOutfit/Run-Authoring.ps1" -Script $ScriptPath `
    -Log 'Saved/chainmail-interlace-commandlet-20260929.log'
