"""Patch only 15 left-finger quaternion curves in R16 empty/cycle actions.

Every arm, wrist, gun, prop, location, scale, duration and R16 event clock is
retained. Profile finger rotations blend to the same hook; all other profile
tracks and all ordinary/normal-reload assets are outside this import.
"""
import bpy, json, math, hashlib, copy
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent;S=O.parent;R16=S/'Super90LoaderR16_20261009'
scene_file=R16/'Super90_Speedloader_R16.blend'
bpy.ops.wm.open_mainfile(filepath=str(scene_file))
rig=bpy.data.objects['SK_Super90'];scene=bpy.context.scene;scene.render.fps=60
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest}
fit=json.loads((O/'hand_target.json').read_text())
finger=[n for n in fit['rotation_bones'] if '_metacarpal_' not in n]
hook={n:Matrix(fit['finger_local'][n]).to_quaternion() for n in finger}
opened={n:Matrix(fit['open_local'][n]).to_quaternion() for n in finger}
for n in ('thumb_02_l','thumb_03_l'):opened[n]=hook[n]
native=json.loads((S/'Super90Foregrips20261007/native.json').read_text())
def umat(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
C=Matrix.Diagonal((100,-100,100,1))
K={n:(C@rest[n]).inverted()@umat(native['rest'][n]) for n in rest}
def ue_q(n,basis):return (K[parents[n]].inverted()@local_rest[n]@basis@K[n]).to_quaternion()
clocks=[json.loads((S/f'Super90LoaderR{rev}_20261009/timing.json').read_text())['source_frames'] for rev in (16,15,14)]
def lut(values,f):
    i=min(len(values)-2,max(0,math.floor(f)));u=max(0.,min(1.,f-i))
    return values[i]*(1-u)+values[i+1]*u
def rack_time(branch,f):
    if branch=='cycle':return 16+f*52/66
    for values in clocks:f=lut(values,f)
    return f-114
def phase(f,a,b):
    x=max(0.,min(1.,(f-a)/(b-a)));return x*x*x*(x*(x*6-15)+10)
order={'index':0,'middle':1,'ring':2,'pinky':3,'thumb':4}
def target(n,t):
    k=order[n.split('_')[0]]
    cover=phase(t,22,26)*(1-phase(t,49,57))
    close=phase(t,27+k*.32,32.6+k*.10)*(1-phase(t,44+k*.06,45.2+k*.12))
    q=opened[n].slerp(hook[n],close)
    return local_rest[n].to_quaternion().inverted()@q,cover
def unpack(v):return Quaternion((v[6],*v[3:6]))
ANIM='/Game/Weapons/Super90/Speedloader20261007/Animations/'
families=('vertical','canted','prism','angled')
inputs={fam:json.loads((R16/(fam+'_profiles.json')).read_text()) for fam in families}
profiles={fam:dict(family=fam,clips=[]) for fam in families}
manifest=json.loads((R16/'authoring.json').read_text())
report=dict(revision='LoaderR17-20261009',source_blend=str(scene_file),
    source_sha256=hashlib.sha256(scene_file.read_bytes()).hexdigest(),
    method='Finger-only partial hook and release from reference; R16 arms/wrist and clocks unchanged',
    modified_bones=finger,retained_clock=str(R16/'timing.json'),reference_frames=[293,298,302,308],
    hand_rotation_changed=False,runtime_tested=False,clips=[])
X=O/'Exports';X.mkdir(exist_ok=True)
for clip in manifest['clips']:
    name=clip['name']
    if '_normal_' in name:continue
    branch='cycle' if name.endswith('_cycle') else 'empty'
    end=round(clip['duration']*60);action=bpy.data.actions[name]
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    bag=action.layers[0].strips[0].channelbag(action.slots[0])
    curves={(c.data_path,c.array_index):c for c in bag.fcurves}
    # Read first, then write: later samples must never depend on earlier edits.
    samples=[]
    for f in range(end+1):
        scene.frame_set(f);bpy.context.view_layer.update()
        samples.append({n:rig.pose.bones[n].matrix_basis.copy().decompose() for n in finger})
    rotation_keys={n:[] for n in finger};old_ue=[];new_ue=[];goal_ue=[];weights=[]
    for f,row in enumerate(samples):
        t=rack_time(branch,f);old={};new={};goal={};ws={}
        for n,(pos,q,scale) in row.items():
            dest,w=target(n,t);final=q.slerp(dest,w) if w else q.copy()
            if rotation_keys[n] and final.dot(rotation_keys[n][-1])<0:final.negate()
            rotation_keys[n].append(final)
            old[n]=ue_q(n,Matrix.LocRotScale(pos,q,scale))
            new[n]=ue_q(n,Matrix.LocRotScale(pos,final,scale))
            goal[n]=ue_q(n,Matrix.LocRotScale(pos,dest,scale));ws[n]=w
        old_ue.append(old);new_ue.append(new);goal_ue.append(goal);weights.append(ws)
    for n,keys in rotation_keys.items():
        for axis in range(4):
            c=curves[(f'pose.bones["{n}"].rotation_quaternion',axis)]
            # Existing integer keys stay in place; untouched samples retain
            # their original floating-point value and interpolation metadata.
            for key in c.keyframe_points:
                f=round(key.co.x)
                if weights[f][n]>0:key.co.y=keys[f][axis]
            c.update()
    for fam in families:
        src=next(c for c in inputs[fam]['clips'] if c['base'].endswith(name))
        out=copy.deepcopy(src);tracks={t['bone']:t for t in out['tracks']}
        for n in finger:
            if n not in tracks:
                tracks[n]=dict(bone=n,times=[f/60 for f in range(end+1)],values=[0,0,0,0,0,0,1,0,0,0]*(end+1))
                out['tracks'].append(tracks[n])
            track=tracks[n]
            for i,sec in enumerate(track['times']):
                f=round(sec*60);w=weights[f][n]
                if not w:continue
                value=track['values'][i*10:(i+1)*10]
                original=unpack(value)@old_ue[f][n]
                corrected=original.slerp(goal_ue[f][n],w)
                delta=corrected@new_ue[f][n].inverted();delta.normalize()
                if delta.w<0:delta.negate()
                track['values'][i*10+3:i*10+7]=[delta.x,delta.y,delta.z,delta.w]
        profiles[fam]['clips'].append(out)
    scene.frame_start=0;scene.frame_end=end;scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    path=X/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    record=copy.deepcopy(clip);record.update(file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    report['clips'].append(record);print('R17_FINGERS_AUTHORED',name,flush=True)
for fam,p in profiles.items():(O/(fam+'_profiles.json')).write_text(json.dumps(p,separators=(',',':')),encoding='utf-8')
rig.animation_data.action=bpy.data.actions['A_Super90_loader_empty_7'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=180;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_R17.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_LOADER_R17_AUTHORED',len(report['clips']),'hand-only clips',flush=True)
