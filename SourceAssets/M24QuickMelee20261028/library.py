import bpy,json,math,bisect,ast
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadRelease20261028/M24_ReloadRelease_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig']
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
rest={n:Matrix(m) for n,m in source['rest'].items()};parents=source['parents'];names=list(rest)
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
ue=json.loads((O/'ue_before.json').read_text());K=Matrix.Diagonal((1,-1,1,1))
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
def clone(row):return {n:m.copy() for n,m in row.items()}
def under(n,p):
    while n:
        if n==p:return True
        n=parents.get(n)
    return False
def ease(x):
    x=max(0,min(1,x));return x*x*x*(10+x*(-15+6*x))
def unpack(v):return Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10])
def sample(track,t):
    ts=track['times'];values=track['values']
    if len(ts)==1:return unpack(values[:10])
    i=max(0,min(len(ts)-2,bisect.bisect_right(ts,t)-1));w=max(0,min(1,(t-ts[i])/(ts[i+1]-ts[i])))
    a,b=unpack(values[i*10:i*10+10]),unpack(values[i*10+10:i*10+20])
    return a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w)
def pose(role,t,family='base',layer=True):
    clip=ue['clips'][role];f=min(t*clip['fps'],clip['keys']-1);i=min(int(f),clip['keys']-2);w=f-i
    entry=next(c for c in ue['profiles'][family] if c['base']==clip['path'])
    tracks={v['bone']:v for v in entry['tracks']};out={};locals={}
    for j,n in enumerate(names):
        a,b=unpack(clip['poses'][str(i)][j]),unpack(clip['poses'][str(i+1)][j])
        p,q,sc=a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w)
        if layer and n in tracks:
            dp,dq,ds=sample(tracks[n],t);p+=dp;q=dq@q;sc+=ds
        locals[n]=K@Matrix.LocRotScale(p,q,sc)@K
        out[n]=out[parents[n]]@locals[n] if parents[n] else locals[n]
    return out,locals

if __name__=='__main__':
    idle,_=pose('idle',0)
    body=bpy.data.objects['M24_base'];pts=[body.matrix_world@v.co for v in body.data.vertices]
    rear=min(p.y for p in pts);pad=[p for p in pts if p.y<rear+.008]
    stock=Vector((sum(p.x for p in pad)/len(pad),rear,sum(p.z for p in pad)/len(pad)))
    root_local=rest['WPN_root'].inverted()@stock
    skin_stock=idle['WPN_root']@root_local
    layout={'stock_source_m':list(stock),'stock_root_cm_ue':list(K.to_3x3()@root_local*100),
            'camera_stock_cm':list(C@skin_stock),
            'camera_held_bones_cm':{n:list(C@idle[n].translation) for n in ('WPN_root','clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r')},
            'weapon_camera_forward':list((C.to_3x3()@idle['WPN_root'].to_3x3()@rest['WPN_root'].inverted().to_3x3()@Vector((0,1,0))).normalized()),
            'clip_duration':(ue['clips']['quick_melee']['keys']-1)/ue['clips']['quick_melee']['fps'],
            'stock_sockets':ue['stock_sockets']}
    (O/'layout.json').write_text(json.dumps(layout,indent=2),encoding='utf-8')
    print('M24_NATIVE_LAYOUT',json.dumps(layout),flush=True)
