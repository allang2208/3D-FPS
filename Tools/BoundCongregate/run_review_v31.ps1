$ErrorActionPreference='Stop'
. "$PSScriptRoot/build_review_v31.ps1" -AssetsOnly
Wait-BCBuildWindow
Write-Output 'Reviewing saved M-88 blueprint and capture transitions in a transient world.'
& "$bcEngine/Binaries/Win64/UnrealEditor-Cmd.exe" "$bcProject/FPSGAME.uproject" -run=BoundCongregateRigReview -CaptureV31 -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/review-final.log" *> "$bcOutput/review-final-console.log"
if($LASTEXITCODE -ne 0){throw "M-88 targeted review failed. See $bcOutput/review-final.log"}
Get-Content -LiteralPath "$bcOutput/capture-review.txt"
