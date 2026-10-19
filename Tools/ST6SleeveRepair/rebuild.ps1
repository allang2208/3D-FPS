param([string]$RunTag=(Get-Date -Format 'yyyyMMdd-HHmmss'),[int]$ResumeAfterCaptureProcess=0)
$ErrorActionPreference='Stop';$projectRoot='D:/FPS3D/FPSGAME';$batchRoot=Join-Path $projectRoot 'SourceAssets/ST6SleeveRepair20261018'
Push-Location $projectRoot
try{
    if($ResumeAfterCaptureProcess -gt 0){
        while(Get-Process -Id $ResumeAfterCaptureProcess -ErrorAction SilentlyContinue){
            try{Wait-Process -Id $ResumeAfterCaptureProcess -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}
        }
        if(-not (Test-Path -LiteralPath (Join-Path $batchRoot 'before.json'))){throw 'Queued source capture did not complete.'}
    }else{
        & Tools/ST6SleeveRepair/run_asset.ps1 -Script capture.py -ReceiptName ('capture-'+$RunTag)
        if($LASTEXITCODE -ne 0){throw 'Native capture did not complete; do not author from stale geometry.'}
    }
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b -t 6 --python Tools/ST6SleeveRepair/author.py *> (Join-Path $batchRoot ('author-'+$RunTag+'.log'))
    if($LASTEXITCODE -ne 0){throw 'Native sleeve authoring failed.'}
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b -t 6 --python Tools/ST6SleeveRepair/save_editable.py *> (Join-Path $batchRoot ('editable-'+$RunTag+'.log'))
    if($LASTEXITCODE -ne 0){throw 'Editable sleeve export failed.'}
    & Tools/ST6SleeveRepair/run_asset.ps1 -Script save_assets.py -ReceiptName ('save-'+$RunTag)
    if($LASTEXITCODE -ne 0){throw 'Sleeve save incomplete; preserve receipt for resumption.'}
    Write-Output 'ST6_NATIVE_SLEEVE_REPAIR_FINISHED'
}finally{Pop-Location}
