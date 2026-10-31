param([int]$Start=0,[int]$End=11)
$ErrorActionPreference='Stop';$urbanRun=Get-Date -Format 'yyyyMMdd-HHmmss'
for($urbanBatch=$Start;$urbanBatch -le $End;$urbanBatch++) {
    $urbanName='riverfront_batch_{0:d2}' -f $urbanBatch
    Write-Output "URBAN_RELOCATION_BEGIN $urbanName"
    & 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1' -PythonScript (Join-Path $PSScriptRoot ($urbanName+'.py')) -QueueWaitSeconds 900 -OutputFile (Join-Path $PSScriptRoot ($urbanName+'-'+$urbanRun+'.log')) -MaxOutputChars 1800
    if($LASTEXITCODE -ne 0){throw "Landscape relocation stopped at $urbanName"}
}
