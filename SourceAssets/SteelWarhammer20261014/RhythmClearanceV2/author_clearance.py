"""Fit the existing attack family's shoulder cuts outside the camera envelope.

The hand/tool group retains its grasp, both arm segments retain their lengths,
and the elbow plane is transported continuously from each accepted source pose.
No renderer or game is started by this production job.
"""
import ast,copy,json,math,itertools
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ComboV1/Warhammer_Combo_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<warhammer_baking>','exec'))
module=ast.parse((ROOT/'SourceAssets/PickaxeSightline20260919/author_attack.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'frame_rotation','axial_delta','unwrap'}],type_ignores=[]),'<arm_frames>','exec'))
FPS=150;source={};paths={};D='/Game/Weapons/SteelWarhammer20261014';B='/Game/Items/ProductionTools/RusticPickaxe20260919'
for clip in ('Swing','HitRecover'):
    name='A_RusticPickaxe_'+clip
    old=bpy.data.actions.get(name)
    if old:old.name='REF_ClearanceBefore_'+name
    with bpy.data.libraries.load(str(ROOT/'SourceAssets/PickaxeSightline20260919/Pickaxe_Sightline_Editable.blend'),link=False) as (_,loaded):loaded.actions=[name]
for clip in ('Slash1','Slash2','Slash1Recover','Slash2Recover','Swing','HitRecover'):
    shared=clip in ('Swing','HitRecover');name=('A_RusticPickaxe_' if shared else 'A_Warhammer_')+clip
    action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    duration=.44 if 'Recover' in clip else .68
    source[clip]=[];paths[clip]=(B+'/' if shared else D+'/ComboV1/')+name
    for i in range(round(duration*FPS)+1):
        scene.frame_set(i*(2 if shared else 1))
        source[clip].append({b.name:b.matrix.copy() for b in rig.pose.bones})

skin=bpy.data.objects['Warhammer_BareArmsV7']
geometry=json.loads((P/'source_geometry.json').read_text())
points=[rig.matrix_world.inverted()@skin.matrix_world@v.co for v in skin.data.vertices]
groups={g.index:g.name for g in skin.vertex_groups};rings=[]
for ring in geometry['rings']:
    ids=ring['vertices'];p=np.array([[*points[i],1.] for i in ids]);influences={}
    for n in {groups[g.group] for i in ids for g in skin.data.vertices[i].groups if g.weight>1e-6}:
        weights=np.array([sum(g.weight for g in skin.data.vertices[i].groups if groups[g.group]==n) for i in ids])
        influences[n]=(p@np.array(rest[n].inverted()).T,weights)
    rings.append(influences)
# Include extra width above the usual 75-degree vertical view and a 2 cm
# margin for locomotion/entry. This is a source-positioning constraint.
TV=math.tan(math.radians(82/2));TH=TV*16/9;MARGIN=.02
def opening_error(pose):
    errors=[]
    for ring in rings:
        p=sum((local@np.array(pose[n]).T)[:,:3]*w[:,None] for n,(local,w) in ring.items())
        x,d,z=p.T
        errors.append(min(float(np.max(v))+MARGIN for v in (d,TH*d-x,TH*d+x,TV*d-z,TV*d+z)))
    return max(errors)
def weight(clip,i):
    t=i/FPS
    return 1-ease((t-.30)/.14) if 'Recover' in clip else ease(t/.085)*(1-ease((t-.52)/.16))
def fit(original,w,profile,state):
    if w<1e-7:return copy.deepcopy(original),0.
    back,down,out=profile;pose=copy.deepcopy(original);arms={};retreat=0.
    for side in ('l','r'):
        a,e,h=[original[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
        l1,l2=(e-a).length,(h-e).length
        shoulder=a+Vector(((-1 if side=='l' else 1)*out,-back,-down))*w
        d=h-shoulder;reach=(l1+l2)*.985
        if d.x*d.x+d.z*d.z>=reach*reach:return None,1.
        retreat=max(retreat,d.y-math.sqrt(reach*reach-d.x*d.x-d.z*d.z))
        arms[side]=(a,e,h,shoulder,l1,l2)
    delta=Vector((0,-max(0.,retreat),0))
    for side,(a,e,h,shoulder,l1,l2) in arms.items():
        wrist=h+delta;d=wrist-shoulder;length=d.length;axis=d.normalized()
        old_axis=(h-a).normalized();pole=e-a
        pole=(pole-old_axis*pole.dot(old_axis)).normalized()
        pole=old_axis.rotation_difference(axis)@pole
        along=(l1*l1-l2*l2+length*length)/(2*length)
        elbow=shoulder+axis*along+pole*math.sqrt(max(0.,l1*l1-along*along))
        old_u,old_f=(e-a).normalized(),(h-e).normalized()
        new_u,new_f=(elbow-shoulder).normalized(),(wrist-elbow).normalized()
        old_normal=old_u.cross(old_f).normalized();new_normal=new_u.cross(new_f).normalized()
        upper_turn=frame_rotation(new_u,new_normal)@frame_rotation(old_u,old_normal).inverted()
        fore_turn=frame_rotation(new_f,new_normal)@frame_rotation(old_f,old_normal).inverted()
        upper_delta=Matrix.Translation(shoulder)@upper_turn.to_matrix().to_4x4()@Matrix.Translation(-a)
        lower_delta=Matrix.Translation(elbow)@fore_turn.to_matrix().to_4x4()@Matrix.Translation(-e)
        pose['clavicle_'+side].translation+=shoulder-a
        for stem in ('upperarm','upperarm_twist_01','upperarm_twist_02'):
            n=stem+'_'+side;pose[n]=upper_delta@original[n]
        hand_deform=original['hand_'+side].to_quaternion()@rest['hand_'+side].to_quaternion().inverted()
        rest_fore=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
        old_full=(hand_deform@rest_fore).rotation_difference(old_f)@hand_deform
        new_full=(hand_deform@rest_fore).rotation_difference(new_f)@hand_deform
        extra=unwrap(axial_delta(new_full,fore_turn@old_full,new_f),state.get(side))
        state[side]=extra
        for n,station in STATIONS[side].items():
            carried=lower_delta@original[n]
            q=Quaternion(new_f,extra*station)@carried.to_quaternion()
            pose[n]=Matrix.LocRotScale(carried.translation,q,original[n].to_scale())
    for n in pose:
        if n=='WPN_root' or n.startswith(('hand_','thumb','index','middle','ring','pinky')):pose[n].translation+=delta
    return pose,retreat

# One correction for all stages avoids switching shoulder positions on contact.
profiles=sorted(itertools.product((0.,.02,.04,.06,.08),(.0,.01,.02),(.0,.01,.02)),key=lambda p:p[0]**2+1.5*p[1]**2+2*p[2]**2)
chosen=None
for profile in profiles:
    valid=True
    for clip,sequence in source.items():
        state={}
        for i,original in enumerate(sequence):
            posed,retreat=fit(original,weight(clip,i),profile,state)
            if posed is None or retreat>.10 or opening_error(posed)>0:
                valid=False;break
        if not valid:break
    if valid:chosen=profile;break
if chosen is None:raise RuntimeError('No natural shoulder fit within the 10 cm held-group allowance')
receipt={'profile_back_down_out_m':chosen,'clips':[],'rendered':False,'runtime_tested':False};poses={}
for clip,sequence in source.items():
    state={};poses[clip]=[fit(p,weight(clip,i),chosen,state)[0] for i,p in enumerate(sequence)]
for swing,recovery in (('Slash1','Slash1Recover'),('Slash2','Slash2Recover'),('Swing','HitRecover')):
    poses[recovery][0]=copy.deepcopy(poses[swing][round(.24*FPS)])
for clip,sequence in poses.items():
    name='A_Warhammer_Clearance_'+clip;bake(name,sequence,FPS)
    receipt['clips'].append({'name':name,'base':paths[clip],'duration':(len(sequence)-1)/FPS,'file':str(OUT/(name+'.fbx'))})
rig.animation_data.action=bpy.data.actions['A_Warhammer_Clearance_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Clearance_Editable.blend'))
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('WARHAMMER_CLEARANCE_AUTHORED '+json.dumps(receipt))
