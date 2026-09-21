"""Read source animation transforms for authoring; no render or gameplay test."""
import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parent
records = {}
for role in ['Idle', 'Walk', 'CastPoison', 'ThrowPoisonBottle', 'DeathBackward']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 120
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'Meshy'/('animation_'+role)/'downloads/result_animation_glb_url.glb'))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    a = rig.animation_data.action
    if not a:
        strip = next(s for t in rig.animation_data.nla_tracks for s in t.strips)
        a = strip.action; slot = strip.action_slot
        rig.animation_data.nla_tracks.clear(); rig.animation_data.action = a; rig.animation_data.action_slot = slot
    start,end = a.frame_range
    names = ['Hips','LeftArm','LeftForeArm','LeftHand','RightHand','LeftFoot','RightFoot','Head','headfront']
    record = {'range':list(a.frame_range),'seconds':(end-start)/120,
              'world':list(rig.matrix_world.decompose()[0]),
              'rest':{n: {'p':list((rig.matrix_world@rig.data.bones[n].matrix_local).translation),
                           'q':list((rig.matrix_world@rig.data.bones[n].matrix_local).to_quaternion()),
                           'length':rig.data.bones[n].length} for n in names}, 'samples':[]}
    for phase in [0,.25,.5,.75,1]:
        frame = start+(end-start)*phase
        bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
        record['samples'].append({n:{'p':list((rig.matrix_world@rig.pose.bones[n].matrix).translation),
                                      'q':list((rig.matrix_world@rig.pose.bones[n].matrix).to_quaternion())} for n in names})
    mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    record['mesh']={'name':mesh.name,'vertices':len(mesh.data.vertices),'bounds':[list(mesh.matrix_world@Vector(v)) for v in mesh.bound_box]}
    bone=rig.data.bones['LeftHand']; inv=(rig.matrix_world@bone.matrix_local).inverted()
    group=mesh.vertex_groups.get('LeftHand')
    vertices=[list(inv@mesh.matrix_world@v.co) for v in mesh.data.vertices if group and any(g.group==group.index and g.weight>.5 for g in v.groups)]
    record['groups']=[g.name for g in mesh.vertex_groups]
    record['hand_weights']={n:max((g.weight for v in mesh.data.vertices for g in v.groups if g.group==mesh.vertex_groups[n].index),default=0) for n in ['LeftHand','LeftForeArm','RightHand','RightForeArm']}
    wrist=Vector(record['rest']['LeftHand']['p']); elbow=Vector(record['rest']['LeftForeArm']['p']); axis=(wrist-elbow).normalized()
    points=[mesh.matrix_world@v.co for v in mesh.data.vertices]
    hand=[p for p in points if (p-wrist).length<.20 and (p-wrist).dot(axis)>-.035]
    record['left_hand_geometry']={'min':[min(p[i] for p in hand) for i in range(3)],'max':[max(p[i] for p in hand) for i in range(3)], 'mean':[sum(p[i] for p in hand)/len(hand) for i in range(3)],'axial_range':[min((p-wrist).dot(axis) for p in hand),max((p-wrist).dot(axis) for p in hand)]}
    record['left_hand_local_bounds'] = {'min':[min(v[i] for v in vertices) for i in range(3)],'max':[max(v[i] for v in vertices) for i in range(3)],'count':len(vertices)} if vertices else None
    records[role]=record
(ROOT/'cloud_motion_read.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('CLOUD_SOURCE_READ '+str(ROOT/'cloud_motion_read.json'))
