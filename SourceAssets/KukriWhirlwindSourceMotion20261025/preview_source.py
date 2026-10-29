"""Background visual read of the supplied Meshy spin; never edits a live scene."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
OUT=Path(__file__).resolve().parent
SOURCE=json.loads((OUT.parent/'KukriMeshyWhirlwind20261025/source.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.fps=120
bpy.ops.import_scene.gltf(filepath=SOURCE['original'])
rig=next(o for o in scene.objects if o.type=='ARMATURE')
action=next(a for a in bpy.data.actions if 'Axe_Spin_Attack' in a.name)
rig.animation_data_create()
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
normalizer=bpy.data.objects.new('SourceHeadingOnly',None);scene.collection.objects.link(normalizer)
for o in list(scene.objects):
    if o!=normalizer and o.parent is None:o.parent=normalizer
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.62,.67,.73)
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
scene.world.color=(.055,.065,.085)
scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
bpy.ops.object.camera_add(location=(3.1,-6.5,2.8));camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,1.0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=2.6;scene.camera=camera
ix=SOURCE['names'].index('pelvis');q=SOURCE['reference_world'][ix][3:7];ref=Quaternion((q[3],*q[:3]))
folder=OUT/'SourcePreview';folder.mkdir(exist_ok=True)
times=[0.,.25,.50,.75,1.,1.25,1.5,1.75,2.,2.5]
for i,t in enumerate(times):
    scene.frame_set(round(t*120))
    q=SOURCE['frames'][min(round(t*120),len(SOURCE['frames'])-1)][ix][3:7]
    forward=(Quaternion((q[3],*q[:3]))@ref.inverted())@Vector((0,1,0))
    # Blender and source.json differ by a Y reflection, so their yaw signs differ.
    normalizer.rotation_euler.z=math.atan2(-forward.x,forward.y)
    scene.render.filepath=str(folder/f'{i:02d}.png');bpy.ops.render.render(write_still=True)
(OUT/'source-preview.json').write_text(json.dumps(dict(action=action.name,range=list(action.frame_range),times=times,heading_normalized=True),indent=2))
