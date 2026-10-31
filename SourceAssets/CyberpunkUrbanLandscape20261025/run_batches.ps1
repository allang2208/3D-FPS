param([int]$Start=0,[int]$End=23)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$runStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
for($batchIndex=$Start;$batchIndex -le $End;$batchIndex++) {
    $batchName='batch_{0:d2}' -f $batchIndex
    Write-Output "URBAN_IMPORT_BEGIN $batchName"
    & 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1' -PythonScript (Join-Path $taskRoot ($batchName+'.py')) -QueueWaitSeconds 900 -RequestTimeoutSeconds 900 -OutputFile (Join-Path $taskRoot ($batchName+'-'+$runStamp+'.log')) -MaxOutputChars 2200
    if($LASTEXITCODE -ne 0){throw "Production batch failed: $batchName"}
    Write-Output "URBAN_IMPORT_END $batchName"
}
