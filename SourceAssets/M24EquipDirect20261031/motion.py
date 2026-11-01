import json,ast,math,bisect
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
D=json.loads((O/'before.json').read_text());names=D['names'];parents=D['parents']
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
for name in ('qlerp','sample'):
    exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
def compose(role,frame,family):
    data=D['clips'][role];clip=next(c for c in D['profiles'][family]['clips'] if c['base']==data['path'])
    tracks={t['bone']:t for t in clip['tracks']};out={};local={}
    lo=max(0,min(int(frame),data['keys']-1));hi=min(lo+1,data['keys']-1);w=frame-lo
    for j,n in enumerate(names):
        a=data['poses'][str(lo)][j];b=data['poses'][str(hi)][j]
        v=[x+(y-x)*w for x,y in zip(a,b)];v[3:7]=qlerp(a[3:7],b[3:7],w)
        p=Vector(v[:3]);q=Quaternion((v[6],*v[3:6]));s=Vector(v[7:10])
        if n in tracks:
            d=sample(tracks[n],frame/data['fps'],10,'values');p+=Vector(d[:3]);q=Quaternion((d[6],*d[3:6]))@q;s+=Vector(d[7:10])
        local[n]=Matrix.LocRotScale(p,q,s);out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
    return out,local
if __name__=='__main__':
    rows=[];anchor=compose('idle',0,'base')[0]['WPN_root']
    for frame in range(0,D['clips']['equip']['keys'],3):
        gun=compose('equip',frame,'base')[0]['WPN_root'];relative=anchor.inverted()@gun
        rows.append({'frame':frame,'offset_in_idle_gun_cm':[round(v*100,3) for v in relative.translation],'degrees':[round(math.degrees(v),3) for v in relative.to_euler()]})
    (O/'source_motion.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows),flush=True)
