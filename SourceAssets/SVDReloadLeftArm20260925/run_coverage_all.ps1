# Before/after support-arm screen coverage for the ten SVD reload clips.
$ErrorActionPreference = 'Stop'
$bl = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$job = 'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925'
$blends = @{
  'base'     = @{ before = @("$job\..\SVDThumbUp20260923\SVD_base_Editable.blend", 'A_SVD_reload');
                  after  = @("$job\Blends\SVD_base_reload_LeftArm.blend", 'A_SVD_reload') }
  'vertical' = @{ before = @("$job\..\SVDThumbUp20260923\SVD_vertical_Editable.blend", 'A_SVD_vertical_reload');
                  after  = @("$job\Blends\SVD_vertical_reload_LeftArm.blend", 'A_SVD_vertical_reload') }
  'canted'   = @{ before = @("$job\..\SVDThumbUp20260923\SVD_canted_Editable.blend", 'A_SVD_canted_reload');
                  after  = @("$job\Blends\SVD_canted_reload_LeftArm.blend", 'A_SVD_canted_reload') }
  'prism'    = @{ before = @("$job\..\SVDThumbUp20260923\SVD_prism_Editable.blend", 'A_SVD_prism_reload');
                  after  = @("$job\Blends\SVD_prism_reload_LeftArm.blend", 'A_SVD_prism_reload') }
  'angled'   = @{ before = @("$job\..\SVDThumbUp20260923\SVD_angled_Editable.blend", 'A_SVD_angled_reload');
                  after  = @("$job\Blends\SVD_angled_reload_LeftArm.blend", 'A_SVD_angled_reload') }
}
$empty = @{
  'base'     = @{ before = @("$job\..\SVDChargeGrasp20260924\SVD_base_Grasp.blend", 'A_SVD_reload_empty');
                  after  = @("$job\Blends\SVD_base_reload_empty_LeftArm.blend", 'A_SVD_reload_empty') }
  'vertical' = @{ before = @("$job\..\SVDChargeGrasp20260924\SVD_vertical_Grasp.blend", 'A_SVD_vertical_reload_empty');
                  after  = @("$job\Blends\SVD_vertical_reload_empty_LeftArm.blend", 'A_SVD_vertical_reload_empty') }
  'canted'   = @{ before = @("$job\..\SVDChargeGrasp20260924\SVD_canted_Grasp.blend", 'A_SVD_canted_reload_empty');
                  after  = @("$job\Blends\SVD_canted_reload_empty_LeftArm.blend", 'A_SVD_canted_reload_empty') }
  'prism'    = @{ before = @("$job\..\SVDChargeGrasp20260924\SVD_prism_Grasp.blend", 'A_SVD_prism_reload_empty');
                  after  = @("$job\Blends\SVD_prism_reload_empty_LeftArm.blend", 'A_SVD_prism_reload_empty') }
  'angled'   = @{ before = @("$job\..\SVDChargeGrasp20260924\SVD_angled_Grasp.blend", 'A_SVD_angled_reload_empty');
                  after  = @("$job\Blends\SVD_angled_reload_empty_LeftArm.blend", 'A_SVD_angled_reload_empty') }
}
foreach ($family in @('base', 'vertical', 'canted', 'prism', 'angled')) {
  foreach ($clip in @('reload', 'reload_empty')) {
    $table = if ($clip -eq 'reload') { $blends } else { $empty }
    $entry = $table[$family]
    $tag = "${family}_${clip}"
    foreach ($phase in @('before', 'after')) {
      $pair = $entry[$phase]
      & $bl --factory-startup -b -t 4 --python "$job\coverage_sweep.py" -- $clip 4 $pair[0] $pair[1] "${tag}_${phase}" '270,350' 2>&1 |
        Select-String -Pattern "^COVERAGE_WORST" | ForEach-Object { "$tag $phase $($_.Line)" }
    }
  }
}
'COVERAGE_ALL_DONE'
