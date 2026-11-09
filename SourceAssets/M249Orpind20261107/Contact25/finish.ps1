$ErrorActionPreference='Stop'
$blend='E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
while(@(Get-CimInstance Win32_Process -Filter "Name='blender.exe'" | Where-Object {$_.CommandLine -like '*Contact25\fit_returns.py*'}).Count){Start-Sleep -Seconds 3}
Write-Output 'CONTACT25_STAGE dense contact sweep'
& py -3.11 "$PSScriptRoot/dense_family_files.py" prepare
if($LASTEXITCODE -ne 0){throw 'Contact family inputs failed'}
$workers=@()
foreach($family in @('vertical','canted','prism','angled')){
 $env:CONTACT25_RETURN_FILE="$PSScriptRoot/return_fit_$family.pkl"
 $process=Start-Process -FilePath $blend -ArgumentList @('-b','-t','2','--python',"$PSScriptRoot/dense_returns.py",'--',$family) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$PSScriptRoot/dense_$family.log" -RedirectStandardError "$PSScriptRoot/dense_$family.stderr.log"
 $workers+=@{Family=$family;Process=$process}
}
Remove-Item Env:CONTACT25_RETURN_FILE
foreach($job in $workers){$job.Process.WaitForExit();if($job.Process.ExitCode -ne 0){throw "Contact sweep failed: $($job.Family)"};Write-Output "CONTACT25_FAMILY_FINISHED $($job.Family)"}
& py -3.11 "$PSScriptRoot/dense_family_files.py" merge
if($LASTEXITCODE -ne 0){throw 'Contact sweep has unresolved frames'}
$dense=Get-Content -LiteralPath "$PSScriptRoot/dense_all.json" -Raw | ConvertFrom-Json
if(@($dense.PSObject.Properties).Count -ne 10){throw 'Incomplete return coverage'}
foreach($row in $dense.PSObject.Properties){if($row.Value.remaining_over_1_8mm -gt 0){throw "Contact remains in $($row.Name)"}}
Write-Output 'CONTACT25_STAGE author profile rows'
& py -3.11 "$PSScriptRoot/publish_profiles.py" *> "$PSScriptRoot/publish_profiles.log"
if($LASTEXITCODE -ne 0){throw 'Profile authoring failed'}
& py -3.11 "$PSScriptRoot/check_candidate.py" *> "$PSScriptRoot/check_candidate.log"
if($LASTEXITCODE -ne 0){throw 'Candidate check failed'}
$auth=Get-Content -LiteralPath "$PSScriptRoot/authoring.json" -Raw | ConvertFrom-Json
foreach($row in $auth.PSObject.Properties){if($row.Value.arm_length_error_cm -gt 0.001 -or $row.Value.outside_left_world_change -gt 0.0000001){throw "Scope/arm length changed in $($row.Name)"}}
Write-Output 'CONTACT25_STAGE save five existing profiles'
& "$PSScriptRoot/assets.ps1" -Script install.py
Write-Output 'CONTACT25_STAGE native UE animation review'
& "$PSScriptRoot/run.ps1" -Manifest manifest.json -Label saved
Write-Output 'CONTACT25_STAGE saved surface review and preview'
& $blend -b -t 4 --python "$PSScriptRoot/depths.py" -- saved *> "$PSScriptRoot/depths_saved.log"
if($LASTEXITCODE -ne 0){throw 'Saved surface review failed'}
& py -3.11 "$PSScriptRoot/audit.py" saved *> "$PSScriptRoot/audit_saved.log"
if($LASTEXITCODE -ne 0){throw 'Saved continuity review failed'}
& py -3.11 "$PSScriptRoot/sheets.py" saved *> "$PSScriptRoot/sheets_saved.log"
if($LASTEXITCODE -ne 0){throw 'Review sheets failed'}
& py -3.11 "$PSScriptRoot/video.py" saved *> "$PSScriptRoot/video_saved.log"
if($LASTEXITCODE -ne 0){throw 'Preview encoding failed'}
Write-Output 'CONTACT25_STAGE complete; native surfaces and images await inspection'
