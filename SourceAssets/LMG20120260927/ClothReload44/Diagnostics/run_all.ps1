param([switch]$SkipAuthor, [switch]$SkipBaseline)
$ErrorActionPreference = 'Continue'
$d = 'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44'
$log = "$d\Diagnostics\run_all.log"
"start $(Get-Date -Format s)" | Out-File -Encoding utf8 $log
if (-not $SkipAuthor) {
    python -X utf8 "$d\author_motion.py" base vertical canted prism angled 2>&1 | Select-String 'AUTHORED|Error|Trace' | Out-File -Append -Encoding utf8 $log
}
foreach ($f in 'base', 'vertical', 'canted', 'prism', 'angled') {
    python -X utf8 "$d\Diagnostics\diagnose.py" "r44_$f" "$d\Tracks\$($f)_tracks.json.gz" --step 6 --garments --swap 2.45,2.80 2>&1 | Select-String 'Error|Trace' | Out-File -Append -Encoding utf8 $log
    if (-not $SkipBaseline) {
        python -X utf8 "$d\Diagnostics\diagnose.py" "c33_$f" "D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothFeed33\$($f)_tracks.json.gz" --step 6 --garments 2>&1 | Select-String 'Error|Trace' | Out-File -Append -Encoding utf8 $log
    }
    python -X utf8 "$d\Diagnostics\check_swap_offscreen.py" "$d\Tracks\$($f)_tracks.json.gz" 2.45 2.80 2>$null | Out-File -Append -Encoding utf8 $log
    "diag $f done $(Get-Date -Format s)" | Out-File -Append -Encoding utf8 $log
}
"end $(Get-Date -Format s)" | Out-File -Append -Encoding utf8 $log
