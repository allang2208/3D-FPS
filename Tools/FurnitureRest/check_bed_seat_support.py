"""Measure buttock support, not merely absence of furniture penetration."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedSupportedV9')
saved='--saved' in sys.argv
sys.argv=['seat-support','--','--v2' if saved else '--candidate','--all','--review',str(OUT/('ReviewSaved' if saved else 'Support')),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text();exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
dom=[geo['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in geo['weights']]
ids=np.array([i for i,b in enumerate(dom) if b.startswith(('pelvis','thigh'))])[::2]
lookup=json.loads((OUT/'Geometry/index.json').read_text());report=[]
for profile in config['furniture']:
    kind=profile['slots'][0]['kind']
    if kind not in profiles:continue
    slot=profile['slots'][0];scale=np.array(profile.get('scale',[1,1,1]));seat=np.array(slot['seat'])*scale;seat[2]-=config['types'][kind]['surface_height']
    turn=np.array(Matrix.Rotation(math.radians(slot['yaw']-90),3,'Z'));g=json.loads(Path(lookup[profile['mesh']]).read_text())
    tree=BVHTree.FromPolygons((np.array(g['positions'])*scale).tolist(),g['triangles'],all_triangles=True)
    take=rig['clips'][f'Rest.{kind}.Enter'];poses=np.array(take['frames']);samples=[]
    for time in np.arange(1.6,5.81,.15):
        p=time/take['duration']*(len(poses)-1);j=min(int(p),len(poses)-2);f=mix(poses[j],poses[j+1],p-j);v=skin(f)[ids]@turn.T+seat;gaps=[]
        hip=turn@fk(f)[ix['pelvis'],:3,3]+seat
        v=v[(np.linalg.norm(v[:,:2]-hip[:2],axis=1)<18)&(v[:,2]<hip[2]-2)&(v[:,2]>hip[2]-25)]
        for point in v:
            hit,_,_,_=tree.ray_cast(Vector(point)+Vector((0,0,10)),Vector((0,0,-1)),40)
            if hit is not None and hit.z>hip[2]-25:gaps.append(float(point[2]-hit.z))
        samples.append([round(float(time),2),min(gaps) if gaps else None])
    row={'kind':kind,'mesh':profile['mesh'],'samples':samples,'maximum_gap_cm':max(v for t,v in samples if v is not None),'minimum_gap_cm':min(v for t,v in samples if v is not None)}
    report.append(row);print('SEAT_SUPPORT',kind,row['minimum_gap_cm'],row['maximum_gap_cm'],flush=True)
(OUT/('seat_support_saved.json' if saved else 'seat_support.json')).write_text(json.dumps(report,indent=2))
