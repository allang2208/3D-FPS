import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'M24CustomScope20261026/Donor/Source/source/arms@sniper.fbx'))
s=bpy.context.scene;r=bpy.data.objects['Armature'];bolt=bpy.data.objects['bolt']
report={'objects':[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'dims':list(o.dimensions)} for o in s.objects],
 'rest':{b.name:[list(v) for v in r.matrix_world@b.matrix_local] for b in r.data.bones},'poses':{},'parts':{}}
for f in range(1,202):
 s.frame_set(f);bpy.context.view_layer.update()
 report['poses'][str(f)]={b.name:[list(v) for v in r.matrix_world@b.matrix] for b in r.pose.bones}
 report['parts'][str(f)]={n:[list(v) for v in bpy.data.objects[n].matrix_world] for n in ('sniper','bolt','boltrear','base')}
(O/'raw_reference.json').write_text(json.dumps(report))
for ob in s.objects:
 if ob.type=='MESH':ob.color=(.64,.69,.73,1) if ob.name=='armmesh' else (.17,.20,.23,1)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True
s.world=bpy.data.worlds.new('RawWorld');s.world.color=(.055,.065,.075)
s.render.resolution_x=720;s.render.resolution_y=480;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.4
folder=O/'ReferenceFrames/raw';folder.mkdir(parents=True,exist_ok=True)
for f in (1,17,20,25,30,35,40,46,110,120,130,140):
 s.frame_set(f);bpy.context.view_layer.update();target=bolt.matrix_world.translation
 cam.location=target+Vector((-.3,.13,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(folder/(str(f)+'.png'));bpy.ops.render.render(write_still=True)
print('RAW_REFERENCE_SAVED',flush=True)
