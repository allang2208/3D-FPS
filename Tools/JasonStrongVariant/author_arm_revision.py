"""Explicit R3 entry point for saving, reading, analyzing, or building the source."""
import runpy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from arm_refinement import ArmRefinedShape
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R3_ArmsRefined')
settings={'variant_output':OUT,'variant_mesh_name':'SK_Jason_StrongTall_R3',
    'variant_blend_name':'Jason_StrongTall_R3','variant_shape_class':ArmRefinedShape,
    'variant_preview_shots':[('01_front',0),('02_three_quarter',-35)]}
if '--blender' in sys.argv:
    runpy.run_path(str(HERE/'build_blender.py'),run_name='__main__',init_globals=settings)
elif '--analyze' in sys.argv:
    runpy.run_path(str(HERE/'analyze_anatomy.py'),run_name='__main__',init_globals=settings)
else:
    runpy.run_path(str(HERE/'save_variant.py'),run_name='__main__',init_globals=settings)
    runpy.run_path(str(HERE/'capture_anatomy_review.py'),run_name='__main__',init_globals=settings)
