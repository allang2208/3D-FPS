"""Fit a small left-arm bend-plane adjustment on the saved R17 source.

Keep wrist/fingers, gun, loader, lengths and every source sample time. The fit
uses the actual V7 upper-arm opening in the existing authoring camera. No render
or runtime test. Rebuild only the six supporting local tracks and grip deltas.
"""
import bpy, json, math, copy, hashlib
from pathlib import Path
from collections import Counter
from mathutils import Matrix, Vector, Quaternion
import numpy as np

O=Path(__file__).parent; S=O.parent
R16=S/'Super90LoaderR16_20261009'; R17=S/'Super90LoaderR17_20261009'
source=R17/'Super90_Speedloader_R17.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene; scene.render.fps=60
rig=bpy.data.objects['SK_Super90']; rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
names=list(rest); parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
I=Matrix.Identity(4); C=Matrix.Diagonal((100,-100,100,1)); Ci=C.inverted()
changed=['upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
local_rest={n:rest.get(parents[n],I).inverted()@rest[n] for n in names}
def mat(v): return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
native=json.loads((S/'Super90Foregrips20261007/native.json').read_text(encoding='utf-8'))
K={n:(C@rest[n]).inverted()@mat(native['rest'][n]) for n in names}
Ki={n:m.inverted() for n,m in K.items()}
families=('vertical','canted','prism','angled')
inputs={fam:{} for fam in families}
for fam in families:
    for base in (R16,R17):
        for clip in json.loads((base/(fam+'_profiles.json')).read_text(encoding='utf-8'))['clips']:
            inputs[fam][clip['base'].split('/')[-1].split('.')[0]]=clip
profiles={fam:dict(family=fam,clips=[]) for fam in families}
manifest={c['name']:c for c in json.loads((R16/'authoring.json').read_text(encoding='utf-8'))['clips']}

# Mesh-space coordinates and real opening, rather than the upperarm pivot.
mesh=bpy.data.objects['Super90_V7_M4_BareArmsV6']
edges=Counter(tuple(sorted(e)) for p in mesh.data.polygons for e in p.edge_keys)
boundary={i for e,num in edges.items() if num==1 for i in e}
upper_group=mesh.vertex_groups['upperarm_l'].index
mesh_to_rig=rig.matrix_world.inverted()@mesh.matrix_world
verts=[v for v in mesh.data.vertices if sum(g.weight for g in v.groups if g.group==upper_group)>.95]
cap=[mesh_to_rig@v.co for v in verts if v.index in boundary]
surface=[mesh_to_rig@v.co for v in verts[::max(1,len(verts)//160)]]
if not cap: raise RuntimeError('The V7 upper-arm opening is missing from the author source')
cap_h=np.asarray([[*v,1] for v in cap],dtype=float).T
surface_h=np.asarray([[*v,1] for v in surface],dtype=float).T
camera=json.loads((S/'Super90LoaderRepair20261008/author_geometry_r3.json').read_text(encoding='utf-8'))['camera']
cm=Matrix.Translation(Vector(camera['location']))@Quaternion(camera['rotation']).to_matrix().to_4x4()@C
cam_matrix=np.asarray(cm,dtype=float)
tan_v=math.tan(math.radians(37.5)); tan_h=tan_v*16/9
rest_upper_inv=rest['upperarm_l'].inverted()

def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)
def weight(f,end):
    ramp=min(18,end*.2)
    return smooth(f/ramp)*smooth((end-f)/ramp)
def rotate_about_arm(p,angle):
    a=p['upperarm_l'].translation; axis=(p['hand_l'].translation-a).normalized()
    return Matrix.Translation(a)@Quaternion(axis,angle).to_matrix().to_4x4()@Matrix.Translation(-a)
def surface_cost(p,angle):
    trans=cam_matrix@np.asarray(rotate_about_arm(p,angle)@p['upperarm_l']@rest_upper_inv,dtype=float)
    c=trans@cap_h; x,y,z=c[:3]
    # Two centimetres of authored clearance around the actual open boundary.
    penetration=np.minimum.reduce((z+tan_v*x,y+tan_h*x,-y+tan_h*x,-z+tan_v*x))+2.
    penetration=np.where(x>0,np.maximum(0,penetration),0)
    v=trans@surface_h; x,y,z=v[:3]
    visible=(x>0)&(np.abs(y)<tan_h*x)&(np.abs(z)<tan_v*x)
    close=np.where(visible,np.maximum(0,14-x),0)
    return float(20*np.max(penetration)**2+2*np.mean(penetration**2)+np.max(close)**2)

def adapt_profile(base,clip,f):
    delta={t['bone']:t['values'][f*10:(f+1)*10] for t in clip['tracks']}
    ue={n:C@base[n]@K[n] for n in names}; result={}
    for n in names:
        par=parents[n]; local=ue.get(par,I).inverted()@ue[n]
        if n in delta:
            d=delta[n]; pos,q,scale=local.decompose()
            local=Matrix.LocRotScale(pos+Vector(d[:3]),Quaternion((d[6],*d[3:6]))@q,scale+Vector(d[7:10]))
        result[n]=result.get(par,I)@local
    return {n:Ci@result[n]@Ki[n] for n in names}

fore_axis=rest['hand_l'].translation-rest['lowerarm_l'].translation
stations={n:max(0.,min(1.,(rest[n].translation-rest['lowerarm_l'].translation).dot(fore_axis)/fore_axis.length_squared)) for n in changed if n.startswith('lowerarm_') and n!='lowerarm_l'}
def repair(p,angle):
    if abs(angle)<1e-8:return p
    out=dict(p); move=rotate_about_arm(p,angle)
    for n in changed:
        if n!='hand_l':out[n]=move@p[n]
    # Spread only the new axial difference across the existing forearm skin
    # stations, preserving R17's skin hinge and the exact original hand matrix.
    fa=(p['hand_l'].translation-out['lowerarm_l'].translation).normalized()
    carried=move.to_quaternion()@p['hand_l'].to_quaternion()
    dq=p['hand_l'].to_quaternion()@carried.inverted()
    twist=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)
    twist=(twist+math.pi)%(2*math.pi)-math.pi
    elbow=out['lowerarm_l'].translation; wrist=p['hand_l'].translation
    for n,station in stations.items():
        centre=elbow.lerp(wrist,station); turn=Quaternion(fa,twist*station)
        pos,q,scale=out[n].decompose()
        out[n]=Matrix.LocRotScale(centre+turn@(pos-centre),turn@q,scale)
    out['hand_l']=p['hand_l']
    return out

def local_ue(p,n): return K.get(parents[n],I).inverted()@p.get(parents[n],I).inverted()@p[n]@K[n]
def patch_action(action,rows):
    bag=action.layers[0].strips[0].channelbag(action.slots[0])
    curves={(c.data_path,c.array_index):c for c in bag.fcurves}
    for n in changed:
        values=[]
        for p in rows:
            basis=local_rest[n].inverted()@p.get(parents[n],I).inverted()@p[n]
            pos,q,scale=basis.decompose()
            if values and values[-1][1].dot(q)<0:q.negate()
            values.append((pos,q,scale))
        for prop,field,size in (('location',0,3),('rotation_quaternion',1,4),('scale',2,3)):
            for axis in range(size):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)]
                for key in curve.keyframe_points:
                    f=round(key.co.x)
                    if 0<f<len(rows)-1:key.co.y=values[f][field][axis]
                curve.update()

X=O/'Exports';X.mkdir(exist_ok=True)
report=dict(revision='LoaderR19-20261009',source_blend=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    method='V7 open-boundary fit by smooth shoulder-wrist bend-plane rotation; fixed hand and source clock',
    changed_bones=changed,runtime_tested=False,rendered=False,clips=[],fit={})
for branch,end in (('normal',144),('empty',180),('cycle',66)):
    name='A_Super90_loader_'+(branch if branch=='cycle' else branch+'_7')
    action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    base=[]
    for f in range(end+1):
        scene.frame_set(f);bpy.context.view_layer.update()
        base.append({b.name:b.matrix.copy() for b in rig.pose.bones})
    family_poses={fam:[adapt_profile(p,inputs[fam][name],f) for f,p in enumerate(base)] for fam in families}
    candidates=range(-36,37,2)
    # One constant signed adjustment with smooth entry/exit, shared by all five
    # grip variants. No per-frame sign switches or changes to shoulder/wrist paths.
    fitting=[(f,p) for rows in [base,*family_poses.values()] for f,p in enumerate(rows) if f%3==0 and weight(f,end)>.05]
    def cost(degrees):
        costs=[surface_cost(p,math.radians(degrees)*weight(f,end)) for f,p in fitting]
        return max(costs)+.2*sum(costs)/len(costs)+.005*degrees*degrees
    degree=min(candidates,key=cost)
    report['fit'][branch]=dict(bend_plane_degrees=degree,entry_exit_frames=min(18,end*.2),author_cost=cost(degree))
    print('R19_ARM_FIT',branch,degree,flush=True)
    if degree==0:
        continue  # The existing cycle-only arm already clears this fitting target.
    new=[repair(p,math.radians(degree)*weight(f,end)) for f,p in enumerate(base)]
    new_family={fam:[repair(p,math.radians(degree)*weight(f,end)) for f,p in enumerate(rows)] for fam,rows in family_poses.items()}
    counts=[0] if branch=='cycle' else range(1,8)
    for count in counts:
        clip_name='A_Super90_loader_'+(branch if count==0 else branch+'_'+str(count))
        target=bpy.data.actions[clip_name];patch_action(target,new)
        rig.animation_data.action=target;rig.animation_data.action_slot=target.slots[0]
        scene.frame_start=0;scene.frame_end=end;scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        file=X/(clip_name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
            add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
        record=copy.deepcopy(manifest[clip_name]);record.update(file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest());report['clips'].append(record)
        for fam in families:
            out=copy.deepcopy(inputs[fam][clip_name]);tracks={t['bone']:t for t in out['tracks']}
            for n in changed:
                values=[];previous=None
                for p,a in zip(new,new_family[fam]):
                    b=local_ue(p,n);t=local_ue(a,n);q=t.to_quaternion()@b.to_quaternion().inverted();q.normalize()
                    if (previous is not None and q.dot(previous)<0) or (previous is None and q.w<0):q.negate()
                    previous=q;values.extend([*(t.translation-b.translation),q.x,q.y,q.z,q.w,*(t.to_scale()-b.to_scale())])
                track=dict(bone=n,times=[f/60 for f in range(end+1)],values=values)
                if n in tracks:tracks[n].update(track)
                else:out['tracks'].append(track)
            profiles[fam]['clips'].append(out)
        print('R19_ARM_AUTHORED',clip_name,flush=True)
for fam,payload in profiles.items():(O/(fam+'_profiles.json')).write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
rig.animation_data.action=bpy.data.actions['A_Super90_loader_empty_7'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=180;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_R19.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_LOADER_R19_AUTHORED',len(report['clips']),flush=True)
