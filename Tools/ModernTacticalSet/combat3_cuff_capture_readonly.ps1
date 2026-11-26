$ErrorActionPreference='Stop'
$cuffProject='D:/FPS3D/FPSGAME'
$cuffRoot="$cuffProject/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1"
for($cuffBatch=0;$cuffBatch -lt 6;$cuffBatch++){
    # This script only reads asset reference meshes and writes source JSON.
    # It neither changes assets/components nor evaluates a running game pose.
    & "$cuffProject/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$cuffProject/Tools/ModernTacticalSet/combat3_cuff_capture.py" -OutputFile "$cuffRoot/Logs/read-gloves-$cuffBatch.txt" -MaxOutputChars 1500 -QueueWaitSeconds 3600 -RequestTimeoutSeconds 1800
    if($LASTEXITCODE -ne 0){throw 'Read-only glove capture stopped'}
    $cuffState=Get-Content -LiteralPath "$cuffRoot/captured.json" -Raw | ConvertFrom-Json
    if($cuffState.completed -and $cuffState.rows.Count -eq 51){break}
}
if(-not $cuffState.completed){throw 'Glove sources incomplete'}
