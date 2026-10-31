from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
r=runpy.run_path(str(R/'build_assets.py'))
i=next(i for i,row in enumerate(r['G']['meshes']) if row['key']=='P2_Ground')
r['meshes'](i,i+1)
print('RIVERFRONT_BATCH_SAVED',1,flush=True)
