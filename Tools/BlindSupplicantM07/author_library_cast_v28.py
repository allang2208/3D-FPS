"""Fit one mature full-body cast and split it at a shared, continuous pose."""
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).parent))
import author_library_sweep_v27 as base

ROOT = base.ROOT/'LibraryCastV28'
OUT = ROOT/'Motion'
FPS, DURATION, GATHER = 60,2.4,1.1

def sample_pose(frames, time, source_duration, ordered):
    index = min(len(frames)-1,max(0.,time/source_duration*(len(frames)-1)))
    a = int(math.floor(index))
    b = min(a+1,len(frames)-1)
    weight = index-a
    result = {}
    # Local-space resampling retains fixed bone lengths and the donor's
    # coordinated joint motion when stretching .5 s into a giant's 2.4 s cast.
    for bone in ordered:
        n,parent = bone.name,bone.parent.name if bone.parent else None
        first = frames[a][parent].inverted()@frames[a][n] if parent else frames[a][n]
        second = frames[b][parent].inverted()@frames[b][n] if parent else frames[b][n]
        local = base.matrix(first.translation.lerp(second.translation,weight),
                            first.to_quaternion().slerp(second.to_quaternion(),weight))
        result[n] = result[parent]@local if parent else local
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    record = json.loads((ROOT/'native_cast_v28.json').read_text(encoding='utf-8'))
    native_rest,samples = base.read_native(record)
    bpy.ops.wm.open_mainfile(filepath=str(base.SOURCE))
    rig = base.v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones,key=lambda p:len(p.bone.parent_recursive))
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    idle = base.v17.cache_action(rig,bpy.data.actions['A_M07_Idle_PalmArmV20'],1,ordered)[0]
    raw,scale = base.registered_poses(native_rest,samples,rest,ordered)
    feet,foot_count = base.foot_support_samples(rig,rest)
    floor = base.support_height(idle,feet)
    envelope = base.body_envelope(rig,rest)
    profile = json.loads(base.clearance.PROFILE.read_text(encoding='utf-8'))
    scene = bpy.context.scene
    scene.render.fps,scene.render.fps_base = FPS,1.
    scene.unit_settings.system,scene.unit_settings.scale_length = 'METRIC',.01
    hidden = {o.name:o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    poses = []
    for i in range(round(DURATION*FPS)+1):
        t = i/FPS
        pose = sample_pose(raw,t/DURATION*record['duration_seconds'],record['duration_seconds'],ordered)
        active = min(1.,max(0.,base.ease(t/.26)*(1.-base.ease((t-(DURATION-.65))/.65))))
        poses.append(base.pose_blend(pose,idle,ordered,active))
    offsets = [base.ground_pose(pose,feet,floor) for pose in poses]
    fits = {s:base.arm_clearance_path(poses,rest,s,envelope,[],smooth_start=0.) for s in ('l','r')}
    for pose in poses:
        base.clearance.inherit_gills(pose,idle,ordered)
        base.clearance.bake_clearance(pose,rest,profile)
    manifest = dict(revision='LibraryCastV28',source=str(OUT/'M07_LibraryCast_V28.blend'),
        source_asset=record['source'],native_retargeter=record['retargeter'],native_pose_cache=record['pose_cache'],
        source_duration_seconds=record['duration_seconds'],fps=FPS,total_duration_seconds=DURATION,
        gather_seconds=GATHER,release_contact_seconds=.30,charge_forward_offset_cm=65.,
        base_attack_range_cm=220.,effective_melee_range_cm=330.,melee_range_multiplier=1.5,
        measured_display_height_cm=310.00057384185493,
        authoring_forward_axis='-Y',source_to_blender_position_scale=scale,
        source_attacking_side='l',root_policy=record['root_policy'],clips={},
        policy='Native full-body SnappySpell source slowed as one continuous action; shared gather/release boundary; original long claw articulation; shoulder-only clearance and baked foot support',
        support_vertex_count=foot_count,idle_support_floor_cm=floor,baked_ground_offsets_cm=offsets,
        shoulder_fit_degrees=fits,melee_animations_modified=False,geometry_modified=False,weights_modified=False,
        new_runtime_ik=False,source_saved=False,animation_fbx_exported=False,ue_imported=False,ue_saved=False,
        tested=False,runtime_tested=False,rendered=False,user_review_pending=True)
    split = round(GATHER*FPS)
    actions = {}
    for role,frames in (('MagicGather',poses[:split+1]),('MagicRelease',poses[split:])):
        action = bpy.data.actions.new('A_M07_'+role+'_LibraryCastV28')
        action.use_fake_user = True
        base.motion.activate(rig,action)
        previous = {}
        for i,pose in enumerate(frames):
            scene.frame_set(i+1)
            base.running.insert_frame(rig,pose,rest,ordered,i+1,previous)
        scene.frame_set(0)
        for bone in ordered:
            bone.matrix_basis = Matrix.Identity(4)
            for prop in ('location','rotation_quaternion','scale'):
                bone.keyframe_insert(data_path=prop,frame=0,group=bone.name)
        for curve in base.running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        base.v15.export(rig,action,fbx,len(frames))
        manifest['clips'][role] = dict(file=str(fbx),action=action.name,frames=len(frames),
            duration_seconds=(len(frames)-1)/FPS,loop=False,root_motion=False,
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsLibraryCastV28/A_M07_'+role)
        actions[role] = action
        print('M07_V28_CAST_EXPORTED '+role,flush=True)
    for name,value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    base.motion.activate(rig,actions['MagicRelease'])
    scene.frame_start,scene.frame_end = 1,len(poses)-split
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'],compress=True)
    manifest.update(source_saved=True,animation_fbx_exported=True)
    (OUT/'library_cast_manifest_v28.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('M07_V28_LIBRARY_CAST_SOURCE_SAVED '+str(OUT),flush=True)

if __name__ == '__main__':
    main()
