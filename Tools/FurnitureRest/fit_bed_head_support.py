"""Fit neutral cervical posture to pillow contact with the runtime head skin."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8')
sys.argv=['head-fit','--','--candidate','--all','--review',str(OUT/'HeadFit'),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
assert head_influences
lookup=json.loads((OUT/'Geometry/index.json').read_text())
skull_ids=np.array([i for i,ws in enumerate(headgeo['weights']) if sum(weight for b,weight in ws if headgeo['bone_names'][b]=='head')>.9])[::12]
body_ids=np.array([i for i,ws in enumerate(geo['weights']) if geo['bone_names'][max(ws,key=lambda x:x[1])[0]].startswith(('spine','neck','pelvis'))])[::8]
bind=fk(ref);spines=['spine_01','spine_02','spine_03','spine_04','spine_05'];rows={}
for kind,profile in profiles.items():
    slot=next(s for s in profile['slots'] if s['kind']==kind);scale=np.array(profile.get('scale',[1,1,1]));seat=np.array(slot['seat'])*scale;seat[2]-=config['types'][kind]['surface_height']
    turn=np.array(Matrix.Rotation(math.radians(slot['yaw']-90),3,'Z'))
    g=json.loads(Path(lookup[profile['mesh']]).read_text());vs=np.array(g['positions'])*scale
    tree=BVHTree.FromPolygons(vs.tolist(),g['triangles'],all_triangles=True)
    high=Vector([0,0,float(vs[:,2].max()+20)]);loc,n,_,_=tree.find_nearest(high);sign=1 if n.dot(high-loc)>0 else -1
    f0=np.array(rig['clips'][f'Rest.{kind}.Idle']['frames'][0]);w0=fk(f0)
    angles={b:math.degrees(math.atan2((w0[ix[b],:3,:3]@bind[ix[b],:3,:3].T)[2,1],(w0[ix[b],:3,:3]@bind[ix[b],:3,:3].T)[1,1])) for b in spines}
    def evaluate(f):
        hp=skinhead(f);skull=hp[skull_ids]@turn.T+seat;gaps=[]
        for p in skull:
            hit,_,_,_=tree.ray_cast(Vector(p)+Vector((0,0,35)),Vector((0,0,-1)),90)
            if hit is not None:gaps.append(float(p[2]-hit.z))
        penetration=0.
        for p in np.vstack([skin(f)[body_ids],hp[::20]])@turn.T+seat:
            loc,n,_,distance=tree.find_nearest(Vector(p),10)
            if loc is not None and n.dot(Vector(p)-loc)*sign<-.7:
                votes=0
                for direction in ((1,.37,.21),(-.22,1,.41),(.31,-.18,1)):
                    direction=Vector(direction).normalized();origin=Vector(p);hits=0
                    for _ in range(64):
                        hit,_,_,_=tree.ray_cast(origin,direction,1000)
                        if hit is None:break
                        hits+=1;origin=hit+direction*.003
                    votes+=hits%2
                if votes>=2:penetration=max(penetration,float(distance))
        return min(gaps),penetration
    print('CURRENT_HEAD',kind,evaluate(f0),flush=True)
    best=None
    for delta in (0,2,4,6,8,10,12):
        for neck in (86,90,94,98,102,106,110,114,120,126,132) if kind=='Hospital' else (86,90,94,98,102,106,110,114):
            f=f0.copy();desired={b:angles[b]+delta for b in spines};desired.update(neck_01=neck,neck_02=neck-1,head=90)
            for b,angle in desired.items():setrot(f,ix[b],np.array(Matrix.Rotation(math.radians(angle),3,'X'))@bind[ix[b],:3,:3])
            gap,depth=evaluate(f);score=100*depth+abs(gap-.45)+.015*delta+.002*abs(neck-94)
            if gap<-.2:score+=100*abs(gap)
            if best is None or score<best[0]:best=(score,desired,gap,depth)
    rows[kind]={'angles':best[1],'skull_gap_cm':best[2],'body_penetration_cm':best[3]}
    print('FITTED_HEAD',kind,rows[kind],flush=True)
(OUT/'head_fit.json').write_text(json.dumps(rows,indent=2))
