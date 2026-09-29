"""Rebuild retained reactions, library locomotion, and the selected melee attack."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

ROOT=Path(__file__).resolve().parent
# Retain separately authored locomotion revisions when rebuilding reactions.
retained_contract=json.loads((ROOT/'animation_contract.json').read_text(encoding='utf-8')) if (ROOT/'animation_contract.json').exists() else {}
OUT=ROOT/'final';OUT.mkdir(exist_ok=True)
FPS=60
metadata=json.loads((ROOT/'native_retarget.json').read_text(encoding='utf-8'))
cache={}
for name,spec in metadata.items():
    role=name.replace('A_SpitterRaw_','')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=spec['fbx'])
    donor=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    action=donor.animation_data.action;scene=bpy.context.scene
    rate=scene.render.fps/scene.render.fps_base;start=action.frame_range[0]
    frames=[]
    for i in range(round(spec['seconds']*FPS)+1):
        f=start+i/FPS*rate;scene.frame_set(math.floor(f),subframe=f%1)
        frames.append({b.name:donor.matrix_world@b.matrix for b in donor.pose.bones})
    cache[role]={'rest':{b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones},'frames':frames,'seconds':spec['seconds']}

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SpitterZombie_Meshy_Source.blend'))
scene=bpy.context.scene;scene.render.fps=FPS;scene.render.fps_base=1
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH']
rig.animation_data_create();rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
world_rest={n:rig.matrix_world@m for n,m in rest.items()}
inv=rig.matrix_world.inverted();ordered=list(rig.pose.bones)
for b in ordered:b.rotation_mode='QUATERNION'

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

def source_pose(role,phase):
    raw=cache[role];frames=raw['frames'];index=phase*(len(frames)-1)
    lo=int(index);hi=min(lo+1,len(frames)-1);alpha=index-lo
    matrices={}
    for b in ordered:
        name=b.name;a=frames[lo][name];c=frames[hi][name]
        q=a.to_quaternion().slerp(c.to_quaternion(),alpha)
        delta=q@raw['rest'][name].to_quaternion().inverted()
        q=(inv.to_quaternion()@delta@world_rest[name].to_quaternion()).normalized()
        bone=rig.data.bones[name]
        if bone.parent:
            pos=matrices[bone.parent.name]@(rest[bone.parent.name].inverted()@rest[name]).translation
        else:
            pos=inv@a.translation.lerp(c.translation,alpha)
            if role in ['Idle','Walk','Dizzy','Stagger']:
                drift=frames[-1][name].translation-frames[0][name].translation
                pos-=inv.to_3x3()@Vector((drift.x*phase,drift.y*phase,0))
        m=Matrix.LocRotScale(pos,q,Vector((1,1,1)));matrices[name]=m
        b.matrix_basis=((rest[bone.parent.name].inverted()@rest[name]).inverted()@matrices[bone.parent.name].inverted()@m
            if bone.parent else rest[name].inverted()@m)
    bpy.context.view_layer.update()

def ground():
    deps=bpy.context.evaluated_depsgraph_get();low=float('inf')
    for mesh in meshes:
        ob=mesh.evaluated_get(deps);skin=ob.to_mesh()
        low=min(low,min((ob.matrix_world@v.co).z for v in skin.vertices));ob.to_mesh_clear()
    m=rig.pose.bones['Hips'].matrix.copy();m.translation+=inv.to_3x3()@Vector((0,0,.003-low))
    rig.pose.bones['Hips'].matrix=m;bpy.context.view_layer.update()

def keys(action,frame,previous):
    for b in ordered:
        q=b.rotation_quaternion.copy()
        if b.name in previous and q.dot(previous[b.name])<0:q.negate()
        b.rotation_quaternion=q;previous[b.name]=q.copy()
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=frame,group=b.name)

def export(role,action,seconds,source):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+meshes:ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    path=OUT/('A_Spitter_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',path_mode='STRIP')
    report[role]={'file':str(path),'seconds':seconds,'fps':FPS,'source':source,'loop':role in ['Idle','Walk','Dizzy']}
    print('SPITTER_AUTHORED',role,seconds,flush=True)

report={}
durations={'Idle':4.,'Death':2.}
for role in list(cache):
    seconds=durations.get(role,cache[role]['seconds'])
    intervals=round(seconds*FPS);seconds=intervals/FPS
    action=bpy.data.actions.new('A_Spitter_'+role);action.use_fake_user=True;rig.animation_data.action=action
    scene.frame_start=0;scene.frame_end=intervals;previous={};first_pose=None
    for f in range(intervals+1):
        scene.frame_set(f);phase=f/intervals
        source_pose(role,phase)
        ground()
        if f==0:first_pose={b.name:b.matrix_basis.copy() for b in ordered}
        if f==intervals and role in ['Idle','Walk','Dizzy']:
            for b in ordered:b.matrix_basis=first_pose[b.name]
        keys(action,f,previous)
    export(role,action,seconds,'Mesh2Motion CC0, native UE IK, original Meshy bind lengths and skin grounding')

# Prone recovery uses the same established grounded roll prefix as other humanoids.
source=bpy.data.actions['A_Spitter_LayToIdle'];rig.animation_data.action=source
if source.slots:rig.animation_data.action_slot=source.slots[0]
samples=[]
for i in range(round(report['LayToIdle']['seconds']*FPS)+1):
    scene.frame_set(i);samples.append({b.name:b.matrix_basis.copy() for b in ordered})
scene.frame_set(0);initial=rig.pose.bones['Hips'].matrix.copy()
axis=(rig.pose.bones['Head'].matrix.translation-initial.translation).normalized()
action=bpy.data.actions.new('A_Spitter_ProneToIdle');action.use_fake_user=True;rig.animation_data.action=action
roll_frames=48;scene.frame_start=0;scene.frame_end=roll_frames+len(samples)-1;previous={}
for f in range(scene.frame_end+1):
    scene.frame_set(f)
    for b in ordered:b.matrix_basis=samples[max(0,f-roll_frames)][b.name]
    bpy.context.view_layer.update()
    if f<roll_frames:
        roll=Quaternion(axis,math.pi*(1-smooth(f/roll_frames)))
        rig.pose.bones['Hips'].matrix=Matrix.LocRotScale(initial.translation,roll@initial.to_quaternion(),Vector((1,1,1)))
        bpy.context.view_layer.update();ground()
    keys(action,f,previous)
export('ProneToIdle',action,scene.frame_end/FPS,'Fitted LayToIdle plus authored 0.8 second grounded roll')
rig.animation_data.action=bpy.data.actions['A_Spitter_Idle'];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SpitterZombie_Animated.blend'))
(ROOT/'animation_contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# The active movement/attack revision uses the imported zombie library.
# Produce LibraryMotionV7/native.json with retarget_library.py before rebuilding.
# Historical V3-V6 authoring sources remain available but are not the active output.
attack_author=ROOT/'LibraryMotionV7/author_library_motion.py'
exec(compile(attack_author.read_text(encoding='utf-8'),str(attack_author),'exec'),{'__file__':str(attack_author),'__name__':'__main__'})

# Current ordinary melee is the user-selected D, fitted to the original skin.
final_attack_author=ROOT/'AttackD_V12/author_attack_d.py'
exec(compile(final_attack_author.read_text(encoding='utf-8'),str(final_attack_author),'exec'),{'__file__':str(final_attack_author),'__name__':'__main__'})
rebuilt_contract=json.loads((ROOT/'animation_contract.json').read_text(encoding='utf-8'))
for role in ['Walk','MovementVariants','MeleePoison']:
    if role in retained_contract:rebuilt_contract[role]=retained_contract[role]
rebuilt_contract['Attack']=json.loads((ROOT/'AttackD_V12/authoring.json').read_text(encoding='utf-8'))['attack']
for field in ['attack_damage','attack_range_base_cm']:
    if field in retained_contract.get('Attack',{}):rebuilt_contract['Attack'][field]=retained_contract['Attack'][field]
variant_author=ROOT/'AttackVariantsV13/author_variants.py'
exec(compile(variant_author.read_text(encoding='utf-8'),str(variant_author),'exec'),{'__file__':str(variant_author),'__name__':'__main__'})
variant_data=json.loads((ROOT/'AttackVariantsV13/authoring.json').read_text(encoding='utf-8'))
rebuilt_contract['AttackVariants']={'revision':variant_data['revision'],'selection':variant_data['selection'],
    'variants':{'AttackD':rebuilt_contract['Attack'],**variant_data['attacks']}}
(ROOT/'animation_contract.json').write_text(json.dumps(rebuilt_contract,ensure_ascii=False,indent=2),encoding='utf-8')
