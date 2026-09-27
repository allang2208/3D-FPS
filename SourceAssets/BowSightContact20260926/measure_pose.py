import json, math, sys
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME')
after='--after' in sys.argv
src=root/('SourceAssets/BowSightContact20260926/generated_actions.py' if after else 'SourceAssets/DarkBow20260925/ReferenceUpgradeV10/author_actions.py')
ns={'__file__':str(src)}
exec(compile(src.read_text(encoding='utf8').split('bpy.ops.wm.read_factory_settings')[0],str(src),'exec'),ns)
rows=[]
for role,t in [('Idle',0),('Draw',0),('Draw',.7),('Draw',1.4)]:
    pose=ns['pose'](role,t); grip=pose['bow_grip'];inv=grip.inverted()
    skin={n:pose[n]@ns['rest'][n].inverted() for n in pose}
    points=[inv@sum((skin[n]@(ns['R']@Vector(v))*w for n,w in weights.items()),Vector()) for v,weights in zip(ns['data']['positions'],ns['data']['weights'])]
    nock=inv@pose['bow_nock'].translation
    def distance(p,a,b):
        d=b-a;return (p-(a+d*max(0.,min(1.,(p-a).dot(d)/d.length_squared)))).length
    close=[]
    for i,p in enumerate(points):
        weights=ns['data']['weights'][i]
        if sum(w for n,w in weights.items() if n.endswith('_l'))<.5:continue
        dist=min(distance(p,nock,Vector(v)) for v in [(-24.082,.095,69.51),(-24.081,.152,-70.598)])
        close.append((dist,i))
    row={'role':role,'t':t,'bones':{n:list(inv@pose[n].translation) for n in ['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','bow_nock']},'left_string_nearest':sorted(close)[:3]}
    rows.append(row)
out=root/'Saved/BowSightContact20260926';out.mkdir(parents=True,exist_ok=True)
(out/('source-pose-after.json' if after else 'source-pose-before.json')).write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
