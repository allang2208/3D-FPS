$ErrorActionPreference='Stop'
& "$PSScriptRoot/render.ps1" -Label after -Role idle -View ads
& "$PSScriptRoot/render.ps1" -Label after -Role reload -View left -Times '0.48,0.542,0.6,0.8,1.0,1.2,2.16'
& "$PSScriptRoot/render.ps1" -Label after -Role reload_empty -View left -Times '0.542,1.0,1.4'
foreach($view in @('after_reload_left','after_reload_empty_left')){
    python "$PSScriptRoot/cpu_contacts.py" "$PSScriptRoot/$view"
    if($LASTEXITCODE -ne 0){throw "Native contact check failed: $view"}
}
python "$PSScriptRoot/finalize_report.py"
if($LASTEXITCODE -ne 0){throw 'M249 report failed'}
