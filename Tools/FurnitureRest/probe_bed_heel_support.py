"""Report heel-to-mattress spacing for the six lying poses."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
OUT=Path(sys.argv[sys.argv.index('--root')+1]) if '--root' in sys.argv else Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8')
measure='--measure' in sys.argv;saved='--saved' in sys.argv
sys.argv=['heels','--','--v2' if saved else '--candidate','--all','--review',str(OUT/('ReviewSaved' if saved else 'HeelProbe')),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
lookup=json.loads((OUT/'Geometry/index.json').read_text())
dom=[geo['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in geo['weights']]
ids=np.array([i for i,b in enumerate(dom) if b.startswith('foot_') and points[i,1]<-3 and points[i,2]<12])
rows={}
for profile in config['furniture']:
    kind=profile['slots'][0]['kind']
    if kind not in profiles:continue
    slot=next(s for s in profile['slots'] if s['kind']==kind);scale=np.array(profile.get('scale',[1,1,1]));seat=np.array(slot['seat'])*scale;seat[2]-=config['types'][kind]['surface_height']
    turn=np.array(Matrix.Rotation(math.radians(slot['yaw']-90),3,'Z'))
    g=json.loads(Path(lookup[profile['mesh']]).read_text());tree=BVHTree.FromPolygons((np.array(g['positions'])*scale).tolist(),g['triangles'],all_triangles=True)
    f=np.array(rig['clips'][f'Rest.{kind}.Idle']['frames'][0]);v=skin(f)[ids]@turn.T+seat;gaps=[]
    for p in v:
        loc,_,_,_=tree.ray_cast(Vector(p)+Vector((0,0,20)),Vector((0,0,-1)),80)
        if loc is not None:gaps.append(float(p[2]-loc.z))
    print('HEEL_SUPPORT',kind,min(gaps) if gaps else None,flush=True)
    if gaps:rows[kind]=min(rows.get(kind,999),min(gaps) if measure else max(0,min(gaps)-.8))
(OUT/('heel_support_saved.json' if saved else 'heel_support.json') if measure else OUT/'heel_fit.json').write_text(json.dumps(rows,indent=2))
