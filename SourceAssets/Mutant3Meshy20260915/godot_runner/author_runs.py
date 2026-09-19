"""Bake the legacy runner onto the current Meshy skin, preserving other actions."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector
ROOT=Path(__file__).parent; OUT=ROOT/'final'; OUT.mkdir(exist_ok=True)
FPS=120
source_contract=json.loads((ROOT/'source_contract.json').read_text())
source_rig=json.loads((ROOT/'source_rig.json').read_text())
metadata=json.loads((ROOT/'native_retarget.json').read_text())
def activate(rig,action):
    rig.animation_data_create(); rig.animation_data.action=action
    if action and action.slots: rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks: track.mute=True
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'native_retarget/A_Mutant3_GodotRaw_Run.fbx'))
donor=next(o for o in bpy.data.objects if o.type=='ARMATURE')
action=donor.animation_data.action; activate(donor,action)
scene=bpy.context.scene; source_rate=scene.render.fps/scene.render.fps_base
start=action.frame_range[0]; duration=metadata['A_Mutant3_GodotRaw_Run']['seconds']
ref={b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones}
frames=[]
for i in range(round(duration*FPS)+1):
    f=start+i*source_rate/FPS; scene.frame_set(math.floor(f),subframe=f%1)
    frames.append({b.name:donor.matrix_world@b.matrix for b in donor.pose.bones})

# Frozen current skin/combat actions; rebuilding locomotion does not need retired revision2.
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Mutant3_Meshy_CombatBase.blend'))
scene=bpy.context.scene; scene.render.fps=FPS; scene.render.fps_base=1
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
world_rest={n:rig.matrix_world@m for n,m in rest.items()}
inv=rig.matrix_world.inverted(); ordered=list(rig.pose.bones)
for pb in ordered: pb.rotation_mode='QUATERNION'
source_lengths=[]; target_lengths=[]
for side,label in [('Left','L'),('Right','R')]:
    points=[Vector(source_rig['bones'][f'bip_{label}_{part}']['head_world']) for part in ['Thigh','Calf','Foot']]
    source_lengths.append(sum((points[i+1]-points[i]).length for i in range(2)))
    points=[world_rest[side+part].translation for part in ['UpLeg','Leg','Foot']]
    target_lengths.append(sum((points[i+1]-points[i]).length for i in range(2)))
leg_ratio=sum(target_lengths)/sum(source_lengths)
retarget_reference_cms=source_contract['source_reference_speed_mps']*100*leg_ratio

def pose_at(phase):
    index=phase*(len(frames)-1); lo=int(index); hi=min(lo+1,len(frames)-1); alpha=index-lo; mats={}
    for name,r in rest.items():
        a,b=frames[lo][name],frames[hi][name]
        delta=a.to_quaternion().slerp(b.to_quaternion(),alpha)@ref[name].to_quaternion().inverted()
        q=(inv.to_quaternion()@delta@world_rest[name].to_quaternion()).normalized()
        bone=rig.data.bones[name]
        if bone.parent:
            pos=mats[bone.parent.name]@(rest[bone.parent.name].inverted()@r).translation
        else:
            pos=inv@a.translation.lerp(b.translation,alpha)
            drift=inv.to_3x3()@(frames[-1][name].translation-frames[0][name].translation)
            pos-=Vector((drift.x,drift.y,0))*phase
        m=Matrix.LocRotScale(pos,q,Vector((1,1,1))); mats[name]=m
        rig.pose.bones[name].matrix_basis=((rest[bone.parent.name].inverted()@r).inverted()@mats[bone.parent.name].inverted()@m if bone.parent else r.inverted()@m)
    bpy.context.view_layer.update()
    # Preserve flight time; only lift actual penetration after body-size changes.
    deps=bpy.context.evaluated_depsgraph_get(); low=float('inf')
    for mesh in meshes:
        obj=mesh.evaluated_get(deps); data=obj.to_mesh()
        low=min(low,min((obj.matrix_world@v.co).z for v in data.vertices)); obj.to_mesh_clear()
    correction=max(0,.003-low)
    hips=rig.pose.bones['Hips']; m=hips.matrix.copy()
    m.translation+=inv.to_3x3()@Vector((0,0,correction)); hips.matrix=m
    bpy.context.view_layer.update()

clips={}; actions={}
for role,reference_cms in [('Running',240),('RunFast',360)]:
    intervals=round(duration*retarget_reference_cms/reference_cms*FPS)
    old=bpy.data.actions.get('A_Mutant3_'+role)
    if old: old.name='BeforeGodotRunner_'+old.name; old.use_fake_user=True
    action=bpy.data.actions.new('A_Mutant3_'+role); action.use_fake_user=True
    activate(rig,action); scene.frame_start=0; scene.frame_end=intervals
    previous={}; first={}
    for frame in range(intervals+1):
        scene.frame_set(frame); phase=frame/intervals; pose_at(phase)
        if frame==0: first={pb.name:pb.matrix_basis.copy() for pb in ordered}
        seam=max(0,min(1,(phase-(1-.04/duration))/(.04/duration)))
        seam=seam*seam*(3-2*seam)
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
    clips[role]={'source':'running_58f (Godot runner Walk alias)','origin':'Denys Almaral, CC BY 4.0; existing Godot adaptation',
                 'fps':FPS,'frames':[0,intervals],'seconds':intervals/FPS,'loop':True,
                 'runtime_reference_speed_cms':reference_cms}
    actions[role]=action
activate(rig,actions['Running']); scene.frame_start=0; scene.frame_end=clips['Running']['frames'][1]; scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_Meshy_GodotRunner.blend'))
report={'clips':clips,'source_seconds':duration,'leg_length_ratio':leg_ratio,
        'retarget_reference_speed_cms':retarget_reference_cms,
        'state':'Two run clips authored; formal import pending; gameplay not tested'}
(ROOT/'animation_contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GODOT_RUNNER_AUTHORED '+json.dumps(report),flush=True)
