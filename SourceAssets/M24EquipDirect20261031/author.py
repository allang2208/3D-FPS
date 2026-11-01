"""Keep the equip receiver at hip idle and carry its existing bolt contacts."""
from pathlib import Path
exec(compile((Path(__file__).parent/'motion.py').read_text().split("if __name__=='__main__':")[0],'motion','exec'))
import bpy
K=Matrix.Diagonal((1,-1,1,1))
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
rest={n:Matrix(m) for n,m in source['rest'].items()}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
def under(n,p):
    while n:
        if n==p:return True
        n=parents.get(n)
    return False
def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed()
def arm(row,hand,side):
    out={n:m.copy() for n,m in row.items()};u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    beforeU=row[l].translation-row[u].translation;beforeL=row[h].translation-row[l].translation
    S=idle[u].translation;H=hand.translation
    A,B=beforeU.length,beforeL.length;direction=H-S;d=direction.length;axis=direction.normalized()
    if d>=A+B-.0001 or d<=abs(A-B)+.0001:raise RuntimeError(f'Equip {side} target at {time}: reach={d}, native={A+B}')
    pole=row[l].translation-S;pole=(pole-axis*pole.dot(axis)).normalized()
    along=(A*A-B*B+d*d)/(2*d);E=S+axis*along+pole*math.sqrt(max(0,A*A-along*along))
    n0=beforeU.cross(beforeL).normalized();n1=(E-S).cross(H-E).normalized()
    uq=(frame(E-S,n1)@frame(beforeU,n0).transposed()).to_quaternion()@row[u].to_quaternion()
    lq=(frame(H-E,n1)@frame(beforeL,n0).transposed()).to_quaternion()@row[l].to_quaternion()
    U=Matrix.LocRotScale(S,uq,row[u].to_scale());L=Matrix.LocRotScale(E,lq,row[l].to_scale())
    out['clavicle_'+side]=idle['clavicle_'+side].copy()
    for n in names:
        if under(n,h):out[n]=hand@row[h].inverted()@row[n]
        elif under(n,l):out[n]=L@row[l].inverted()@row[n]
        elif under(n,u):out[n]=U@row[u].inverted()@row[n]
    ax=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
    relative=lq.inverted()@hand.to_quaternion()@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
    if relative.w<0:relative=-relative
    roll=2*math.atan2(Vector((relative.x,relative.y,relative.z)).dot(ax),relative.w)
    for j,weight in ((1,1.),(2,.5)):
        n=f'lowerarm_twist_{j:02d}_{side}';lr=local_rest[n]
        out[n]=L@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*weight)@lr.to_quaternion(),lr.to_scale())
    return out
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24GripOutfit20261030/M24_GripOutfit_Editable.blend'),load_ui=False,use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];bpy.context.preferences.filepaths.save_version=0
owned={'WPN_root'}
for side in ('l','r'):
    owned.update(n+'_'+side for n in ('clavicle','upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand'))
owned.update(n for n in names if n.startswith('ik_hand') and n!='ik_hand_root')
patch={};data=D['clips']['equip']
for family in ('base','mag10'):
    entry=next(c for c in D['profiles'][family]['clips'] if c['base']==data['path']);duration=entry['duration']
    idle={n:K@m@K for n,m in compose('idle',0,family)[0].items()};anchor=idle['WPN_root']
    times=sorted({0.,duration,*[i/120 for i in range(int(duration*120)+1)]})
    tracks={n:dict(bone=n,times=times,values=[]) for n in names if n in owned};last={}
    r.animation_data_clear();r.animation_data_create();action=bpy.data.actions.new('A_M24_EquipDirect_'+family);action.use_fake_user=True;r.animation_data.action=action
    for time in times:
        ue,_=compose('equip',time*data['fps'],family);row={n:K@m@K for n,m in ue.items()}
        carry=anchor@row['WPN_root'].inverted();fixed={n:m.copy() for n,m in row.items()}
        changed=carry.translation.length>1e-6 or abs(carry.to_quaternion().w)<1-1e-8
        if changed:
            fixed=arm(fixed,carry@row['hand_l'],'l');fixed=arm(fixed,carry@row['hand_r'],'r')
            for n in names:
                if under(n,'WPN_root') or (n.startswith('ik_hand') and n!='ik_hand_root'):fixed[n]=carry@row[n]
        for n,track in tracks.items():
            loc=fixed[parents[n]].inverted()@fixed[n] if parents[n] else fixed[n]
            target=K@loc@K;p,q,sc=target.decompose()
            f=time*data['fps'];lo=min(int(f),data['keys']-1);hi=min(lo+1,data['keys']-1);w=f-lo
            a=data['poses'][str(lo)][names.index(n)];b=data['poses'][str(hi)][names.index(n)]
            raw=[x+(y-x)*w for x,y in zip(a,b)];raw[3:7]=qlerp(a[3:7],b[3:7],w)
            dq=q@Quaternion((raw[6],*raw[3:6])).inverted()
            if n in last and dq.dot(last[n])<0:dq=-dq
            last[n]=dq.copy();track['values'].extend([*(p-Vector(raw[:3])),dq.x,dq.y,dq.z,dq.w,*(sc-Vector(raw[7:10]))])
        # Keep a full editable pose action; runtime uses the sparse profile layer.
        for n,m in fixed.items():
            loc=fixed[parents[n]].inverted()@m if parents[n] else m
            bone=r.pose.bones[n];bone.rotation_mode='QUATERNION';bone.matrix_basis=local_rest[n].inverted()@loc
            for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=time*120)
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag=strip.channelbag(slot)
                if bag:
                    for fc in bag.fcurves:
                        for key in fc.keyframe_points:key.interpolation='LINEAR'
    patch[family]={'base':data['path'],'duration':duration,'tracks':list(tracks.values())}
bpy.context.scene.render.fps=120;bpy.context.scene.frame_start=0;bpy.context.scene.frame_end=round(duration*120)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_EquipDirect_Editable.blend'))
(O/'equip_patch.json').write_text(json.dumps(patch),encoding='utf-8')
(O/'authoring.json').write_text(json.dumps(dict(scope='equip only, both magazine profiles',sample_rate=120,duration=duration,weapon_anchor='current idle',shoulders='current idle',finger_local_tracks='retained',mechanical_timing='retained',owned_bones=sorted(owned),runtime_tested=False),indent=2))
print('M24_EQUIP_DIRECT_AUTHORED',flush=True)
