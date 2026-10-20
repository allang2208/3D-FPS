param([Parameter(Mandatory=$true)][int]$AuthorPid)
$ErrorActionPreference='Stop'
$author=Get-Process -Id $AuthorPid -ErrorAction SilentlyContinue
if($author){Wait-Process -InputObject $author -Timeout 1200}
if(!(Select-String -LiteralPath "$PSScriptRoot/author-final.log" -Pattern '^SVCH_FOUR_GRIP_PROFILES_AUTHORED$' -Quiet)){
    throw 'Profile authoring did not complete; preserve current UE assets.'
}
& "$PSScriptRoot/run_asset_step.ps1" -ScriptName install_profiles.py -LogStem install
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python "$PSScriptRoot/export_editable.py" *> "$PSScriptRoot/export-editable.log"
if($LASTEXITCODE -ne 0){throw 'Editable source export failed; see export-editable.log.'}
Write-Output 'SVCH_FOREGRIP_DELIVERY_COMPLETE'
