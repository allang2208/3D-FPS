"""Replace two run cycles and the stagger on the original skin, keeping other actions."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).parent; OUT=ROOT/'final'; OUT.mkdir(exist_ok=True)
FPS=120; metadata=json.loads((ROOT/'native_retarget.json').read_text())

def activate(rig,action):
    rig.animation_data_create(); rig.animation_data.action=action
    if action and action.slots: rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks: track.mute=True

cache={}
for role in ['Jog','ZombiePosture','HitChest']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/f'native_retarget/A_Mutant3_R2_{role}.fbx'))
    donor=next(o for o in bpy.data.objects if o.type=='ARMATURE'); action=donor.animation_data.action; activate(donor,action)
    scene=bpy.context.scene; rate=scene.render.fps/scene.render.fps_base; start=action.frame_range[0]
    rest={b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones}
    frames=[]
    for i in range(round(metadata['A_Mutant3_R2_'+role]['seconds']*FPS)+1):
        f=start+i*rate/FPS; scene.frame_set(math.floor(f),subframe=f%1)
        frames.append({b.name:donor.matrix_world@b.matrix for b in donor.pose.bones})
    cache[role]=(rest,frames)

bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'Mutant3_Meshy_Animated.blend'))
scene=bpy.context.scene; scene.render.fps=FPS; scene.render.fps_base=1
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}; world_rest={n:rig.matrix_world@m for n,m in rest.items()}
inv=rig.matrix_world.inverted(); ordered=list(rig.pose.bones)
for pb in ordered: pb.rotation_mode='QUATERNION'

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a))); return t*t*(3-2*t)

def pose(role,phase):
    ref,frames=cache[role]; index=max(0,min(1,phase))*(len(frames)-1)
    lo=int(index); hi=min(lo+1,len(frames)-1); alpha=index-lo; mats={}
    for name,r in rest.items():
        a,b=frames[lo][name],frames[hi][name]
        delta=a.to_quaternion().slerp(b.to_quaternion(),alpha)@ref[name].to_quaternion().inverted()
        q=(inv.to_quaternion()@delta@world_rest[name].to_quaternion()).normalized(); bone=rig.data.bones[name]
        if bone.parent: pos=mats[bone.parent.name]@(rest[bone.parent.name].inverted()@r).translation
        else:
            pos=inv@a.translation.lerp(b.translation,alpha)
            # Actor movement owns travel/knockback. Keep authored bob and stance,
            # but remove accumulated horizontal displacement from the cycle.
            drift=inv.to_3x3()@(frames[-1][name].translation-frames[0][name].translation)
            pos-=Vector((drift.x,drift.y,0))*phase
        m=Matrix.LocRotScale(pos,q,Vector((1,1,1))); mats[name]=m
        rig.pose.bones[name].matrix_basis=((rest[bone.parent.name].inverted()@r).inverted()@mats[bone.parent.name].inverted()@m if bone.parent else r.inverted()@m)
    bpy.context.view_layer.update()

def ground_penetration(allow_lowering):
    deps=bpy.context.evaluated_depsgraph_get(); low=float('inf')
    for mesh in meshes:
        ob=mesh.evaluated_get(deps); data=ob.to_mesh()
        low=min(low,min((ob.matrix_world@v.co).z for v in data.vertices)); ob.to_mesh_clear()
    correction=.003-low
    if not allow_lowering: correction=max(0,correction)
    hips=rig.pose.bones['Hips']; m=hips.matrix.copy(); m.translation+=inv.to_3x3()@Vector((0,0,correction)); hips.matrix=m
    bpy.context.view_layer.update()

# Read the chest recoil maximum from its existing torso rotation, then put that
# pose at the shared reaction clock's 0.1 s hold boundary. It never uses fall keys.
pose('HitChest',0); chest_start=rig.pose.bones['Spine'].matrix.to_quaternion()
peak_phase=0; peak_angle=-1
for i in range(len(cache['HitChest'][1])):
    p=i/(len(cache['HitChest'][1])-1); pose('HitChest',p)
    angle=chest_start.rotation_difference(rig.pose.bones['Spine'].matrix.to_quaternion()).angle
    if angle>peak_angle: peak_phase=p; peak_angle=angle

contract={}; actions={}
for role,intervals in [('Running',96),('RunFast',78),('Stagger',108)]:
    old=bpy.data.actions.get('A_Mutant3_'+role)
    if old: old.name='BeforeRevision2_'+old.name
    action=bpy.data.actions.new('A_Mutant3_'+role); action.use_fake_user=True; activate(rig,action)
    scene.frame_start=0; scene.frame_end=intervals; first={}; previous={}
    for frame in range(intervals+1):
        scene.frame_set(frame); phase=frame/intervals
        if role=='Stagger':
            t=frame/FPS
            source_phase=peak_phase*smooth(0,.1,t) if t<=.6 else peak_phase+(1-peak_phase)*smooth(.6,.9,t)
            pose('HitChest',source_phase); ground_penetration(True)
        else:
            # A small upper-body contribution supplies the zombie posture;
            # Jog retains pelvis, legs, foot contact and the alternating stride.
            pose('ZombiePosture',phase)
            zombie={pb.name:pb.rotation_quaternion.copy() for pb in ordered}
            pose('Jog',phase)
            for name in ['Spine02','Spine01','Spine','neck','Head']:
                pb=rig.pose.bones[name]; pb.rotation_quaternion=pb.rotation_quaternion.slerp(zombie[name],.16)
            for side in ['Left','Right']:
                for suffix in ['Shoulder','Arm','ForeArm','Hand']:
                    pb=rig.pose.bones[side+suffix]; pb.rotation_quaternion=pb.rotation_quaternion.slerp(zombie[pb.name],.12)
            bpy.context.view_layer.update(); ground_penetration(False)
        if frame==0: first={pb.name:pb.matrix_basis.copy() for pb in ordered}
        seam=smooth(1-.05/(intervals/FPS),1,phase) if role!='Stagger' else 0
        for pb in ordered:
            if seam:
                p,q,s=pb.matrix_basis.decompose(); fp,fq,fs=first[pb.name].decompose()
                pb.matrix_basis=Matrix.LocRotScale(p.lerp(fp,seam),q.slerp(fq,seam),s.lerp(fs,seam))
            q=pb.rotation_quaternion.copy()
            if pb.name in previous and previous[pb.name].dot(q)<0: q.negate()
            pb.rotation_quaternion=q; pb.scale=(1,1,1); previous[pb.name]=q.copy()
            for prop in ['location','rotation_quaternion','scale']: pb.keyframe_insert(prop,frame=frame,group=pb.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points: key.interpolation='LINEAR'
    scene.frame_set(0); bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+meshes: ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'A_Mutant3_{role}.fbx'),use_selection=True,
        object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',mesh_smooth_type='FACE',path_mode='STRIP')
    actions[role]=action; contract[role]={'source':'Hit_Chest' if role=='Stagger' else 'Jog + Zombie_Walk_2 upper-body adaptation',
        'origin':'Mesh2Motion CC0','fps':FPS,'frames':[0,intervals],'seconds':intervals/FPS,'loop':role!='Stagger'}
activate(rig,actions['Running']); scene.frame_start=0; scene.frame_end=96; scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_Meshy_Animated_Revision2.blend'))
(ROOT/'animation_contract.json').write_text(json.dumps({'clips':contract,'recoil_source_peak_phase':peak_phase,
    'recoil_source_peak_angle_degrees':math.degrees(peak_angle),'recoil_timing':{'attack':.1,'hold_end':.6,'end':.9},
    'state':'Replacement animations authored; gameplay testing remains with user'},indent=2),encoding='utf-8')
print('MUTANT3_REPLACEMENTS_AUTHORED '+json.dumps(contract),flush=True)
