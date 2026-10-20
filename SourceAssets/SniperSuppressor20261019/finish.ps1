param([int]$IconPid,[int]$ExportPid)
$ErrorActionPreference='Stop'
foreach($taskProcessId in @($IconPid,$ExportPid)){
    $taskProcess=Get-Process -Id $taskProcessId -ErrorAction SilentlyContinue
    if($taskProcess){Wait-Process -InputObject $taskProcess -Timeout 600}
}
if(!(Test-Path -LiteralPath "$PSScriptRoot/icon_authoring.json")){throw 'Production icon is not yet complete.'}
& "$PSScriptRoot/run_asset_step.ps1" -ScriptName install_assets.py -LogStem install
& py -3.11 "$PSScriptRoot/publish_catalog.py"
if($LASTEXITCODE -ne 0){throw 'Catalog publication failed; preserve completed model assets.'}
& "$PSScriptRoot/build.ps1"
Write-Output 'SNIPER_SUPPRESSOR_DELIVERY_COMPLETE'
