import json,runpy
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/RangerCrouchFit20261021/TuckedPairV2');d=json.loads((R/'check.json').read_text());row=max(d['records'][0]['samples'],key=lambda r:r['exposed_triangle_intersections']);clip,index=row['pose'].split('@')
runpy.run_path('D:/FPS3D/FPSGAME/Tools/RangerCrouchFit/render_diagnostic.py',run_name='__main__',init_globals={'CANDIDATE_ROOT':str(R),'USE_POSE_CLEARANCE':False,'CLIP':clip,'SAMPLE':int(index),'OUTPUT_PREFIX':'waist_contact'})
