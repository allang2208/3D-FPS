$ErrorActionPreference='Stop'
& "$PSScriptRoot/run.ps1" -Script publish.py
& "$PSScriptRoot/final_review.ps1"
