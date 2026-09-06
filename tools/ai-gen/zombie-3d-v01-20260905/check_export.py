"""Round-trip actual exported GLB, sample Attack contact, render once."""
import bpy,json,sys
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'zombie-rigged.blend'))
for o in list(bpy.data.objects):
    if o.type in {'MESH','ARMATURE'}:bpy.data.objects.remove(o,do_unlink=True)
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'zombie-preview.glb'))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
actions=list(bpy.data.actions)
print('ROUNDTRIP_ACTIONS',[(a.name,list(a.frame_range)) for a in actions],flush=True)
clip='Death' if '--death' in sys.argv else ('Walk' if '--walk' in sys.argv else 'Attack')
sample_time={'Walk':.6,'Death':2.0,'Attack':.375}[clip]
attack=next(a for a in actions if clip in a.name)
arm.animation_data_create()
for tr in arm.animation_data.nla_tracks:tr.mute=True
arm.animation_data.action=attack
if attack.slots:arm.animation_data.action_slot=attack.slots[0]
scene=bpy.context.scene;scene.frame_set(round(attack.frame_range[0]+sample_time*scene.render.fps))
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.cycles.samples=12
scene.camera.location=(3,-5,1.85);scene.camera.rotation_euler=(Vector((0,-.12,.94))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
if clip=='Death':
    scene.camera.data.ortho_scale=2.65;scene.camera.location=(4,-3,2.6);scene.camera.rotation_euler=(Vector((0,.4,.8))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(ROOT/('export-roundtrip-'+clip.lower()+'.png'));bpy.ops.render.render(write_still=True)
deps=bpy.context.evaluated_depsgraph_get()
report={'sample':f'{clip} +{sample_time}s','actions':[a.name for a in actions],'meshes':[]}
for o in scene.objects:
    if o.type!='MESH' or o.hide_render:continue
    ev=o.evaluated_get(deps);me=ev.to_mesh();vs=[ev.matrix_world @ v.co for v in me.vertices]
    report['meshes'].append({'name':o.name,'bounds_min':[min(v[i] for v in vs) for i in range(3)],'bounds_max':[max(v[i] for v in vs) for i in range(3)]});ev.to_mesh_clear()
if clip=='Walk':
    scene.frame_set(int(attack.frame_range[0]));start=[b.matrix.copy() for b in arm.pose.bones]
    scene.frame_set(int(attack.frame_range[1]));end=[b.matrix.copy() for b in arm.pose.bones]
    report['loop_max_bone_matrix_delta']=max(abs(a[i][j]-b[i][j]) for a,b in zip(start,end) for i in range(4) for j in range(4))
    assert report['loop_max_bone_matrix_delta']<.0001,report
(ROOT/('roundtrip-'+clip.lower()+'-report.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
