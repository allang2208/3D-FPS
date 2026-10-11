"""Preserve R20 choreography, add supported load response and a cupped bolt grasp."""
import bpy,json,math,copy,hashlib,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;sys.path.insert(0,str(O))
from motion import motion,phase,smooth
source=S/'Super90LoaderR20_20261010/Super90_Speedloader_R20.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['SK_Super90'];scene=bpy.context.scene;scene.render.fps=60
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};names=list(rest)
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
I=Matrix.Identity(4);C=Matrix.Diagonal((100,-100,100,1));Ci=C.inverted()
local_rest={n:rest.get(parents[n],I).inverted()@rest[n] for n in names}
def mat(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
native=json.loads((S/'Super90Foregrips20261007/native.json').read_text())
K={n:(C@rest[n]).inverted()@mat(native['rest'][n]) for n in names};Ki={n:v.inverted() for n,v in K.items()}
camera=json.loads((S/'Super90LoaderR20_20261010/camera_current.json').read_text())
CQ=Quaternion(camera['rotation']);cam_to_author=(CQ.to_matrix()@C.to_3x3()).inverted()
axis=[(cam_to_author@Vector(v)).normalized() for v in ((1,0,0),(0,1,0),(0,0,1))]
grasp=json.loads((O/'grasp_target.json').read_text());finger=[n for n in grasp['rotation_bones'] if 'metacarpal' not in n]
target={n:Matrix(grasp['finger_local'][n]) for n in finger};wrist_delta=Matrix(grasp['wrist_local_delta'])
support={side:[f'upperarm_{side}',f'lowerarm_{side}',f'lowerarm_aux_{side}',f'lowerarm_twist_02_{side}',f'lowerarm_twist_01_{side}',f'hand_{side}'] for side in ('l','r')}
changed=['VM_Root',*support['l'],*support['r'],*finger]
raw=json.loads((O/'source_poses.json').read_text());source_rows={b:[{n:Matrix(m) for n,m in p.items()} for p in ps] for b,ps in raw.items()};del raw
families=('vertical','canted','prism','angled');inputs={fam:{} for fam in families}
for fam in families:
    for rev in (16,17,19,20):
        day='20261010' if rev==20 else '20261009'
        for c in json.loads((S/f'Super90LoaderR{rev}_{day}'/(fam+'_profiles.json')).read_text())['clips']:
            inputs[fam][c['base'].split('/')[-1].split('.')[0]]=c
profiles={fam:dict(family=fam,clips=[]) for fam in families}
manifest={c['name']:c for c in json.loads((S/'Super90LoaderR16_20261009/authoring.json').read_text())['clips']}
clocks=[json.loads((S/f'Super90LoaderR{rev}_20261009/timing.json').read_text())['source_frames'] for rev in (16,15,14)]
def rack_time(branch,f):
    if branch=='cycle':return 16+f*52/66
    for values in clocks:
        i=min(len(values)-2,max(0,math.floor(f)));u=max(0,min(1,f-i));f=values[i]*(1-u)+values[i+1]*u
    return f-114
def adapt_profile(base,clip,f):
    delta={t['bone']:t['values'][f*10:(f+1)*10] for t in clip['tracks']}
    ue={n:C@base[n]@K[n] for n in names};result={}
    for n in names:
        par=parents[n];local=ue.get(par,I).inverted()@ue[n]
        if n in delta:
            d=delta[n];pos,q,scale=local.decompose();local=Matrix.LocRotScale(pos+Vector(d[:3]),Quaternion((d[6],*d[3:6]))@q,scale+Vector(d[7:10]))
        result[n]=result.get(par,I)@local
    return {n:Ci@result[n]@Ki[n] for n in names}
def basis(axis,normal):
    x=axis.normalized();z=normal.normalized();y=z.cross(x).normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_quaternion()
def support_hand(p,side,hand,pole_degrees=0):
    a,e0,t0=[p[f'{n}_{side}'].translation for n in ('upperarm','lowerarm','hand')];t=hand.translation
    l1=(e0-a).length;l2=(t0-e0).length;d=(t-a).length
    if not abs(l1-l2)<d<l1+l2:raise RuntimeError('Unreachable grasp '+side)
    ax0=(t0-a).normalized();ax=(t-a).normalized();pole0=(e0-a)-ax0*(e0-a).dot(ax0)
    pole=(Quaternion(ax,math.radians(pole_degrees))@(ax0.rotation_difference(ax)@pole0)).normalized()
    along=(l1*l1-l2*l2+d*d)/(2*d);radius=math.sqrt(max(0,l1*l1-along*along));e=a+ax*along+pole*radius
    norm0=(e0-a).cross(t0-e0).normalized();norm=(e-a).cross(t-e).normalized()
    qu=basis(e-a,norm)@basis(e0-a,norm0).inverted();qf=basis(t-e,norm)@basis(t0-e0,norm0).inverted()
    upper=Matrix.Translation(a)@qu.to_matrix().to_4x4()@Matrix.Translation(-a)
    lower=Matrix.Translation(e)@qf.to_matrix().to_4x4()@Matrix.Translation(-e0)
    out=dict(p);out[f'upperarm_{side}']=upper@p[f'upperarm_{side}'];out[f'lowerarm_{side}']=lower@p[f'lowerarm_{side}']
    fore=(t-e).normalized();dq=hand.to_quaternion()@(qf@p[f'hand_{side}'].to_quaternion()).inverted()
    twist=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fore),dq.w);twist=(twist+math.pi)%(2*math.pi)-math.pi
    ra=rest[f'lowerarm_{side}'].translation;rv=rest[f'hand_{side}'].translation-ra
    for n in support[side]:
        if n in (f'upperarm_{side}',f'lowerarm_{side}',f'hand_{side}'):continue
        station=max(0,min(1,(rest[n].translation-ra).dot(rv)/rv.length_squared));centre=e.lerp(t,station)
        m=lower@p[n];pos,q,scale=m.decompose();turn=Quaternion(fore,twist*station)
        out[n]=Matrix.LocRotScale(centre+turn@(pos-centre),turn@q,scale)
    out[f'hand_{side}']=hand
    return out
digit_order={'index':0,'middle':1,'ring':2,'pinky':3,'thumb':2}
butt_bind=Vector((0.,-.4895,-.8266))
def author_pose(p,branch,f):
    out=dict(p)
    if branch!='normal':
        t=rack_time(branch,f)
        w=phase(t,25.5,33)*(1-phase(t,44,48))
        if w>0:
            dp,dq,ds=wrist_delta.decompose();h=p['hand_l']@Matrix.LocRotScale(dp*w,Quaternion().slerp(dq,w),Vector((1,1,1)))
            out=support_hand(out,'l',h)
        for n in grasp['rotation_bones']:
            par=parents[n];local=p[par].inverted()@p[n]
            if n in target:
                k=digit_order[n.split('_')[0]]
                close=phase(t,26+k*.22,33+k*.06)*(1-phase(t,44+k*.12,46.6+k*.16))
                pos,q,scale=local.decompose();q=q.slerp(target[n].to_quaternion(),close)
                local=Matrix.LocRotScale(pos,q,scale)
            out[n]=out[par]@local
    angles,travel,_=motion(branch,f)
    # Pivot at the stock pad, with only millimetres of shoulder compression.
    pivot=p['WPN_root']@rest['WPN_root'].inverted()@butt_bind
    pitch,yaw,roll=angles
    # Author->UE conversion reflects Y: use the conjugated signs so the
    # named pitch/yaw/roll agree with the camera's FRotator response.
    q=Quaternion(axis[2],math.radians(-yaw))@Quaternion(axis[1],math.radians(pitch))@Quaternion(axis[0],math.radians(roll))
    shift=cam_to_author@Vector(travel)
    move=Matrix.Translation(pivot+shift)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)
    out={n:move@m for n,m in out.items()}
    # The bracing forearm reacts slightly later; the right hand never slips on
    # the pistol grip and its accepted finger pose is untouched.
    elbow=motion(branch,f-1.5)[2]
    if abs(elbow)>1e-7:out=support_hand(out,'r',out['hand_r'],elbow)
    return out
def local_ue(p,n):
    par=parents[n]
    return K[par].inverted()@p[par].inverted()@p[n]@K[n] if par else C@p[n]@K[n]
def patch_action(action,rows):
    bag=action.layers[0].strips[0].channelbag(action.slots[0]);curves={(c.data_path,c.array_index):c for c in bag.fcurves}
    for n in changed:
        values=[]
        for p in rows:
            v=list((local_rest[n].inverted()@p.get(parents[n],I).inverted()@p[n]).decompose())
            if values and values[-1][1].dot(v[1])<0:v[1].negate()
            values.append(v)
        for prop,field,size in (('location',0,3),('rotation_quaternion',1,4),('scale',2,3)):
            for axis in range(size):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)]
                for key in curve.keyframe_points:
                    f=round(key.co.x)
                    if 0<f<len(rows)-1:key.co.y=values[f][field][axis]
                curve.update()
X=O/'Exports';X.mkdir(exist_ok=True)
report=dict(revision='LoaderR21-20261010',source=str(source),method='R20 supported contact response and cupped charging-handle grasp',
    modified_bones=changed,retained_timing='R16: normal 144, empty 180, cycle 66 source frames',runtime_tested=False,clips=[])
for branch,end in (('normal',144),('empty',180),('cycle',66)):
    source_name='A_Super90_loader_'+(branch if branch=='cycle' else branch+'_7');base=source_rows[branch]
    new=[author_pose(p,branch,f) for f,p in enumerate(base)]
    family_rows={fam:[author_pose(adapt_profile(p,inputs[fam][source_name],f),branch,f) for f,p in enumerate(base)] for fam in families}
    for count in ([0] if branch=='cycle' else range(1,8)):
        name='A_Super90_loader_'+(branch if count==0 else branch+'_'+str(count));action=bpy.data.actions[name];patch_action(action,new)
        rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_start=0;scene.frame_end=end;scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        file=X/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
            bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
        record=copy.deepcopy(manifest[name]);record.update(file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest());report['clips'].append(record)
        for fam in families:
            clip=copy.deepcopy(inputs[fam][name]);tracks={t['bone']:t for t in clip['tracks']}
            for n in changed:
                values=[];previous=None
                for p,a in zip(new,family_rows[fam]):
                    b=local_ue(p,n);t=local_ue(a,n);q=t.to_quaternion()@b.to_quaternion().inverted();q.normalize()
                    if (previous is not None and q.dot(previous)<0) or (previous is None and q.w<0):q.negate()
                    previous=q;values.extend([*(t.translation-b.translation),q.x,q.y,q.z,q.w,*(t.to_scale()-b.to_scale())])
                track=dict(bone=n,times=[f/60 for f in range(end+1)],values=values)
                if n in tracks:tracks[n].update(track)
                else:clip['tracks'].append(track)
            profiles[fam]['clips'].append(clip)
        print('R21_AUTHORED',name,flush=True)
for fam,p in profiles.items():(O/(fam+'_profiles.json')).write_text(json.dumps(p,separators=(',',':')),encoding='utf-8')
rig.animation_data.action=bpy.data.actions['A_Super90_loader_empty_7'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_end=180;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_R21.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_R21_AUTHORED',len(report['clips']),flush=True)
