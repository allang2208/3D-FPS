"""Measure torso and skull clearance against the actual ordinary-bed surface."""
import bpy,json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

PROJECT=Path('D:/FPS3D/FPSGAME')
DEST=PROJECT/'SourceAssets/FurnitureRest20261022/MeshyBed20261024'
sys.argv=['support','--','--candidate','--all','--review',str(DEST/'SupportFit'),'--config',str(DEST/'review_config.json')]
code=(PROJECT/'Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
index=json.loads((PROJECT/'SourceAssets/FurnitureRest20261022/RefineV2/Geometry/index.json').read_text())
profile=next(p for p in config['furniture'] if p['slots'][0]['kind']=='Bed' and 'RefinementV2' in p['mesh'])
g=json.loads((PROJECT/'SourceAssets/FurnitureRest20261022/RefineV2/Geometry'/index[profile['mesh']]).read_text())
tree=BVHTree.FromPolygons(g['positions'],g['triangles'],all_triangles=True)
dom=[geo['bone_names'][max(ws,key=lambda v:v[1])[0]] for ws in geo['weights']]
torso_ids=np.array([i for i,n in enumerate(dom) if n=='pelvis' or n.startswith('spine_')])[::3]
skull_ids=np.array([i for i,ws in enumerate(headgeo['weights']) if sum(v for b,v in ws if headgeo['bone_names'][b]=='head')>.9])[::6]
def gap(vertices):
    values=[]
    for p in vertices:
        hit,_,_,_=tree.ray_cast(Vector(p)+Vector((0,0,40)),Vector((0,0,-1)),100)
        if hit is not None:values.append(float(p[2]-hit.z))
    return min(values) if values else 100.
previous=json.loads((DEST/'support_fit.json').read_text()) if (DEST/'support_fit.json').exists() else None
take=rig['clips']['Rest.Bed.Enter'];frames=np.array(take['frames'])
times=[];roots=[];necks=[];observations=[]
for i in sorted(set(list(range(0,len(frames),3))+[len(frames)-1])):
    time=i/30;f=frames[i].copy()
    prior_root=float(np.interp(time,previous['times'],previous['root_z'])) if previous else 0.
    prior_neck=float(np.interp(time,previous['times'],previous['neck_degrees'])) if previous else 0.
    body_gap=gap(skin(f)[torso_ids]);delta=max(0.,.35-body_gap)
    f[ix['pelvis'],2]+=delta
    head_gap=gap(skinhead(f)[skull_ids]);extra=0.
    if head_gap<.25:
        w=fk(f)
        for angle in np.arange(1.,36.):
            h=f.copy()
            for n,factor in [('neck_01',1.),('neck_02',1.),('head',.55)]:
                rotation=np.array(Matrix.Rotation(math.radians(-angle*factor),3,'X'))
                setrot(h,ix[n],rotation@w[ix[n],:3,:3])
            extra=float(angle)
            if gap(skinhead(h)[skull_ids])>=.35:break
    times.append(time);roots.append(prior_root+delta);necks.append(prior_neck+extra)
    observations.append({'time':time,'body_gap':body_gap,'head_gap_after_root':head_gap})
def soften(values):
    # Keep the measured peaks with a small margin; taper over adjacent samples.
    a=np.array(values);out=a.copy()
    for shift,weight in [(1,.8),(2,.45)]:
        out[shift:]=np.maximum(out[shift:],a[:-shift]*weight)
        out[:-shift]=np.maximum(out[:-shift],a[shift:]*weight)
    return out.tolist()
result={'times':times,'root_z':soften(roots),'neck_degrees':soften(necks),'observations':observations}
(DEST/'support_fit.json').write_text(json.dumps(result,indent=2))
print('MESHY_BED_SUPPORT',max(roots),max(necks),flush=True)
