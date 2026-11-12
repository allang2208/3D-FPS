"""Small entry/recovery timing refinement directly from pre-Beast06 ClawV16."""
from pathlib import Path
import json
import math
import bpy

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
SOURCE = BASE/'ClawV16/Delivery'
OUT = BASE/'ClawV17/Delivery'
OUT.mkdir(parents=True,exist_ok=True)
manifest = json.loads((SOURCE/'motion_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'MantisM27_ClawV16.blend'))
scene = bpy.context.scene; scene.render.fps = FPS = 60; scene.render.fps_base = 1.
rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
for track in rig.animation_data.nla_tracks: track.mute = True
names = [bone.name for bone in rig.data.bones]
# Output seconds, original seconds, derivative of the original clock.
# The complete load peak, strike, contact, braking and recoil stay on their
# original clock from .16 through .36 seconds. Only the outer portions change.
TIME_MAP = [(0.,0.,.65),(.06,.045,.95),(.16,.16,1.),(.36,.36,1.),
            (.48,.50,1.15),(.65,.65,.50)]

def source_time(t):
    if .16 <= t <= .36: return t
    for left,right in zip(TIME_MAP,TIME_MAP[1:]):
        if t <= right[0]+1.e-8:
            start,a,ma = left; end,b,mb = right; length = end-start
            x = min(1.,max(0.,(t-start)/length))
            return ((2*x**3-3*x*x+1)*a+(x**3-2*x*x+x)*length*ma
                    +(-2*x**3+3*x*x)*b+(x**3-x*x)*length*mb)
    return TIME_MAP[-1][1]

def activate(action):
    rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]

def read_source(role):
    activate(bpy.data.actions['A_M27_'+role+'_ClawV16']); frames = []
    for i in range(manifest['clips'][role]['frames']):
        scene.frame_set(i+1); pose = {}
        for name in names:
            p,q,s = rig.pose.bones[name].matrix_basis.decompose()
            if frames and q.dot(frames[-1][name][1]) < 0: q.negate()
            pose[name] = (p.copy(),q.copy(),s.copy())
        frames.append(pose)
    return frames

def sample(frames,t):
    cursor = min(len(frames)-1.,max(0.,t*FPS)); nearest = round(cursor)
    if abs(cursor-nearest) < 1.e-6: return frames[nearest]
    i = math.floor(cursor); j = min(i+1,len(frames)-1); a = cursor-i
    return {n:(frames[i][n][0].lerp(frames[j][n][0],a),frames[i][n][1].slerp(frames[j][n][1],a),
               frames[i][n][2].lerp(frames[j][n][2],a)) for n in names}

sources = {role:read_source(role) for role in ['LeftSlash','RightSlash']}
report = {'revision':'ClawV17','status':'candidate_only','source_revision':'ClawV16','fps':FPS,
    'mesh_revision':'BindingV2','clips':{},'time_map_output_source_speed':TIME_MAP,
    'unchanged_source_time_range_seconds':[.16,.36],'contact_window_seconds':[.25,.30],
    'recovery_time_seconds':.10,'retained_motion':'ClawV16 complete dense poses, signed blade paths, body drive and foot support',
    'scope':'Entry and late recovery timing only; no pose reconstruction or donor blending',
    'source_license':manifest['source_license'],'runtime_tested':False,'offline_validated':False,
    'rendered':False,'native_code_changed':False}
for role,frames in sources.items():
    action = bpy.data.actions.new('A_M27_'+role+'_ClawV17'); action.use_fake_user = True; activate(action)
    scene.frame_start,scene.frame_end = 1,len(frames); previous = {}
    for i in range(len(frames)):
        pose = sample(frames,source_time(i/FPS))
        for name in names:
            p,q,s = pose[name]; q = q.copy(); pb = rig.pose.bones[name]
            if name in previous and previous[name].dot(q) < 0: q.negate()
            previous[name] = q.copy(); pb.location = p; pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = q; pb.scale = s
            for channel in ['location','rotation_quaternion','scale']: pb.keyframe_insert(channel,frame=i+1,group=name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points: key.interpolation = 'LINEAR'
    scene.frame_set(1); bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    filename = action.name+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT/filename),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',global_scale=1.,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0.)
    report['clips'][role] = {'file':filename,'frames':len(frames),'seconds':.65,
        'source':'/Game/Monsters/MantisM27/ClawV16/Animations/A_M27_'+role+'_ClawV16',
        'upstream_source':manifest['clips'][role]['source']}
    print('M27_CLAW_V17_LOCAL_REFINEMENT_EXPORTED '+role,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_ClawV17.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M27_CLAW_V17_LOCAL_REFINEMENT_AUTHORED',flush=True)
