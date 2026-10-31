import sys,json
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import build_assets as b
b.report=json.loads((R/'assets_saved.json').read_text('utf8'));b.report['stage']='final_refinement';b.record()
surfaces=b.SURFACES;b.SURFACES={k:v for k,v in surfaces.items() if k in {'CharcoalWeave','FogLinen','OchreCloth','Rug'}}
b.materials();b.SURFACES=surfaces;b.meshes();b.calibrated_instances();b.report['stage']='assets_saved';b.record()
print('BP3_FINAL_MATERIALS_AND_GEOMETRY_SAVED')
