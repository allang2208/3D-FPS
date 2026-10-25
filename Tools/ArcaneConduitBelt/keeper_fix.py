"""Rebuild the three misplaced keeper loops from the corrected author recipe."""
import sys,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import author
P=Path('D:/FPS3D/FPSGAME')
OLD=P/'SourceAssets/ArcaneConduitBelt20261025/ModelR1'
NEW=OLD.parent/'ModelR2'
for folder in ('Exports','Authored'):(NEW/folder).mkdir(parents=True,exist_ok=True)
author.R=NEW;author.E=NEW/'Exports'
inputs=author.read(OLD/'inputs.json');author.write(NEW/'inputs.json',inputs)
reports=[]
for row in inputs['records']:
    belt=author.ArcaneBelt(row)
    belt.author()
    bounds=[]
    deps=author.bpy.context.evaluated_depsgraph_get()
    for ob in belt.objects:
        evaluated=ob.evaluated_get(deps);mesh=evaluated.to_mesh()
        points=[evaluated.matrix_world@v.co for v in mesh.vertices]
        low=min(v.z*100 for v in points);high=max(v.z*100 for v in points)
        if low<min(belt.top)-20 or high>max(belt.top)+20:
            raise RuntimeError('Component outside the waist: '+ob.name+' '+str((low,high)))
        if ob.name.startswith(('LeatherKeeper_','Keeper_Pin_')):
            bounds.append(dict(name=ob.name,z_cm=[low,high]))
        evaluated.to_mesh_clear()
    reports.append(dict(body=row['body'],component_count=len(belt.objects),keepers=bounds,
        waist_top_cm=[float(min(belt.top)),float(max(belt.top))],all_components_within_waist=True))
    print('ARCANE_KEEPER_FIX_AUTHORED',row['body'],flush=True)
author.write(NEW/'keeper-fix.json',dict(completed=True,reason='Reset world coordinates before each leather keeper; pin frame was applied twice',
    source_author_sha256=hashlib.sha256((P/'Tools/ArcaneConduitBelt/author.py').read_bytes()).hexdigest(),
    records=reports,runtime_tested=False))
