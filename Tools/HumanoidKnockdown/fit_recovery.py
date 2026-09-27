"""Bake recovery motions onto each existing skin, preserving bind-pose bone lengths."""
import bpy, json, math, argparse, sys
from pathlib import Path
from mathutils import Matrix, Vector

parser=argparse.ArgumentParser()
parser.add_argument('--root',default='D:/FPS3D/FPSGAME/SourceAssets/HumanoidKnockdown20260926')
parser.add_argument('--loop',action='store_true')
parser.add_argument('--plant-feet',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ROOT = Path(args.root)
OUT = ROOT / 'fitted'
OUT.mkdir(exist_ok=True)
FPS = 60
SOURCES = {
    'FatZombie': ROOT.parent/'FatZombieMeshy20260913/FatZombie_Meshy_Source.blend',
    'Mutant3': ROOT.parent/'Mutant3Khaimera20260923/hand_ground_fix/Mutant3_Claw_Source.blend',
}
META = json.loads((ROOT/'imported_animations.json').read_text())

def activate(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if action and action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True

report = {}
for role, meta in META.items():
    clips = {}
    for clip in meta['clips']:
        name = clip['asset'].split('.')[-1]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(ROOT/(name+'_raw.fbx')))
        donor = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        action = donor.animation_data.action
        activate(donor, action)
        scene = bpy.context.scene
        rate = scene.render.fps / scene.render.fps_base
        start = action.frame_range[0]
        frames = []
        for i in range(round(clip['seconds']*FPS)+1):
            f = start + i/FPS*rate
            scene.frame_set(math.floor(f), subframe=f % 1)
            frames.append({b.name: donor.matrix_world @ b.matrix for b in donor.pose.bones})
        clips[name] = dict(frames=frames, rest={b.name: donor.matrix_world @ b.matrix_local for b in donor.data.bones})
    # The two Meshy imports need their original Blender bind skeleton. The
    # mannequin clips already include their target preview skin and bind pose.
    if role in SOURCES:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCES[role]))
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
    for obj in list(bpy.data.objects):
        if obj not in [rig]+meshes:
            bpy.data.objects.remove(obj, do_unlink=True)
    activate(rig, None)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    world_rest = {n: rig.matrix_world @ m for n,m in rest.items()}
    inv = rig.matrix_world.inverted()
    ordered = list(rig.pose.bones)
    pelvis = 'Hips' if role in SOURCES else 'pelvis'
    for b in ordered:
        b.rotation_mode = 'QUATERNION'

    def update():
        bpy.context.view_layer.update()

    def set_pose(name, matrix):
        rig.pose.bones[name].matrix = matrix
        update()

    def solve_limb(names, dest, pole_offset):
        first, mid, last = [rig.pose.bones[n] for n in names]
        p0,p1,p2 = [p.matrix.translation.copy() for p in [first,mid,last]]
        l1,l2 = (p1-p0).length,(p2-p1).length
        direction = dest-p0
        dist = max(.0001,min(direction.length,l1+l2-.00001))
        direction.normalize()
        along = (l1*l1-l2*l2+dist*dist)/(2*dist)
        pole = p1-p0+pole_offset
        pole -= direction*pole.dot(direction)
        if pole.length < .00001:
            pole = Vector((0,-1,0));pole -= direction*pole.dot(direction)
        pole.normalize()
        elbow = p0+direction*along+pole*math.sqrt(max(0,l1*l1-along*along))
        hand_q = last.matrix.to_quaternion()
        q = (p1-p0).rotation_difference(elbow-p0) @ first.matrix.to_quaternion()
        set_pose(first.name,Matrix.LocRotScale(p0,q,Vector((1,1,1))))
        pm,pe = mid.matrix.translation.copy(),last.matrix.translation.copy()
        q = (pe-pm).rotation_difference(p0+direction*dist-pm) @ mid.matrix.to_quaternion()
        set_pose(mid.name,Matrix.LocRotScale(pm,q,Vector((1,1,1))))
        set_pose(last.name,Matrix.LocRotScale(last.matrix.translation,hand_q,Vector((1,1,1))))

    def solve_arm(side, dest, pole_offset):
        solve_limb([side+n for n in ['Arm','ForeArm','Hand']],dest,pole_offset)

    legs = [[side+n for n in ['UpLeg','Leg','Foot']] for side in ['Left','Right']] if role in SOURCES else [
        ['thigh_l','calf_l','foot_l'],['thigh_r','calf_r','foot_r']]

    torso = []
    if role == 'FatZombie':
        for mesh in meshes:
            groups = {g.index:g.name for g in mesh.vertex_groups}
            for v in mesh.data.vertices:
                if sum(g.weight for g in v.groups if groups.get(g.group) in {'Hips','Spine02','Spine01','Spine','neck'}) > .65:
                    torso.append(inv @ mesh.matrix_world @ v.co)
        rx = max(abs(v.x) for v in torso)+.035
        ymin,ymax = min(v.y for v in torso)-.035,max(v.y for v in torso)+.035
        yc,ry = (ymin+ymax)*.5,(ymax-ymin)*.5

    role_report = {}
    for name, data in clips.items():
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        activate(rig, action)
        scene.frame_start,scene.frame_end = 0,len(data['frames'])-1
        previous = {}
        anchors = []
        first_pose = {}
        for frame, raw in enumerate(data['frames']):
            scene.frame_set(frame)
            if args.loop:
                # Remove accumulated travel while retaining the sway, then close
                # the last quarter second into the first pose of the loop.
                phase=frame/max(1,scene.frame_end)
                tail=max(0,min(1,(frame-(scene.frame_end-15))/15))
                tail=tail*tail*(3-2*tail)
                drift=data['frames'][-1][pelvis].translation-data['frames'][0][pelvis].translation
                raw={n:m.copy() for n,m in raw.items()}
                raw[pelvis].translation-=drift*phase
                raw={n:m.lerp(data['frames'][0][n],tail) for n,m in raw.items()}
            mats = {}
            for pb in ordered:
                bone,n = pb.bone,pb.name
                if n not in raw:
                    mats[n] = mats[bone.parent.name] @ (rest[bone.parent.name].inverted() @ rest[n]) if bone.parent else rest[n]
                    pb.matrix_basis = Matrix.Identity(4)
                    continue
                delta = raw[n].to_quaternion() @ data['rest'][n].to_quaternion().inverted()
                q = (inv.to_quaternion() @ delta @ world_rest[n].to_quaternion()).normalized()
                pos = mats[bone.parent.name] @ (rest[bone.parent.name].inverted() @ rest[n]).translation if bone.parent else inv @ raw[n].translation
                if n == pelvis:
                    pos = inv @ raw[n].translation
                m = Matrix.LocRotScale(pos,q,Vector((1,1,1)))
                mats[n] = m
                pb.matrix_basis = (rest[bone.parent.name].inverted() @ rest[n]).inverted() @ mats[bone.parent.name].inverted() @ m if bone.parent else rest[n].inverted() @ m
            update()
            if torso:
                body = rig.pose.bones['Spine01'].matrix @ rest['Spine01'].inverted()
                for side,sign in [('Left',1),('Right',-1)]:
                    hand = rig.pose.bones[side+'Hand'].matrix.translation.copy()
                    p = body.inverted() @ hand
                    y = (p.y-yc)/ry
                    if .65 < p.z < 1.45 and abs(y) < 1:
                        p.x = sign*max(sign*p.x,rx*math.sqrt(1-y*y)+.045)
                        solve_arm(side,body @ p,body.to_3x3() @ Vector((sign*.045,0,0)))
            # Ground using the deformed skin (back, palms, feet), not pelvis
            # height. This is authoring, and does not run/render the game.
            deps = bpy.context.evaluated_depsgraph_get()
            low = float('inf')
            for mesh in meshes:
                ob = mesh.evaluated_get(deps)
                skin = ob.to_mesh()
                low = min(low,min((ob.matrix_world @ v.co).z for v in skin.vertices))
                ob.to_mesh_clear()
            m = rig.pose.bones[pelvis].matrix.copy()
            m.translation += inv.to_3x3() @ Vector((0,0,.003-low))
            set_pose(pelvis,m)
            if args.plant_feet:
                if not anchors:
                    anchors=[rig.pose.bones[names[-1]].matrix.copy() for names in legs]
                # Keep both feet on their authored starting footprints. Share
                # reach correction through the pelvis before solving each leg.
                drop=0
                for names,anchor in zip(legs,anchors):
                    points=[rig.pose.bones[n].matrix.translation for n in names]
                    length=(points[1]-points[0]).length+(points[2]-points[1]).length
                    offset=points[0]-anchor.translation
                    reach=math.sqrt(max(.00001,(length*.995)**2-offset.x**2-offset.y**2))
                    drop=max(drop,offset.z-reach)
                if drop>0:
                    m=rig.pose.bones[pelvis].matrix.copy();m.translation.z-=drop;set_pose(pelvis,m)
                for names,anchor in zip(legs,anchors):
                    solve_limb(names,anchor.translation,Vector((0,0,0)))
                    set_pose(names[-1],Matrix.LocRotScale(rig.pose.bones[names[-1]].matrix.translation,
                        anchor.to_quaternion(),Vector((1,1,1))))
            if frame==0:first_pose={pb.name:pb.matrix_basis.copy() for pb in ordered}
            if args.loop and frame==scene.frame_end:
                for pb in ordered:pb.matrix_basis=first_pose[pb.name]
                update()
            for pb in ordered:
                q = pb.rotation_quaternion.copy()
                if pb.name in previous and q.dot(previous[pb.name]) < 0:
                    q.negate()
                pb.rotation_quaternion = q
                previous[pb.name] = q.copy()
                pb.scale = (1,1,1)
                for prop in ['location','rotation_quaternion','scale']:
                    pb.keyframe_insert(prop,frame=frame,group=pb.name)
            if frame % 30 == 0:
                print(f'RECOVERY_FIT {name} {frame}/{scene.frame_end}',flush=True)
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
        scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [rig]+meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
            object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
            bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
        role_report[name] = {'file':str(OUT/(name+'.fbx')),'seconds':scene.frame_end/FPS,'fps':FPS,
            'loop':args.loop,'planted_feet':args.plant_feet}
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(role+'_Recovery.blend')))
    report[role] = role_report
    (OUT/'authored_clips.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RECOVERY_FIT_COMPLETE',flush=True)
