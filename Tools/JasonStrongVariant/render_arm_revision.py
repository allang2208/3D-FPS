"""Same-angle R2 versus R3 arm anatomy comparison, cropped to the upper body."""
import json,runpy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R3_ArmsRefined')
REVIEW=OUT/'ArmReview'
before=json.loads((REVIEW/'before_R2.json').read_text())
saved='--saved' in sys.argv
after=json.loads((OUT/'AnatomyReview/derived_saved_mesh.json' if saved else REVIEW/'authored_candidate.json').read_text())
before['head_z_cm']=after['head_z_cm']=4.5
prefix='' if saved else 'draft_'
runpy.run_path(str(HERE/'render_anatomy_review.py'),run_name='__main__',init_globals={
    'review_output':OUT,'review_folder':REVIEW,'review_datasets':[before,after],
    'review_width':2200,'review_height':900,'review_spacing':.93,
    'review_shots':[(prefix+'01_raised_front','shoulders',0,3.8,1.3),
        (prefix+'02_raised_elbow','raised_elbows',-30,3.8,1.3),
        (prefix+'03_rest_three_quarter','rest',-25,3.4,1.3),
        (prefix+'04_raised_high','shoulders_high',0,3.8,1.43)]})
