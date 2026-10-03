"""Produce the modification pictogram from one actual full-height side skin."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parents[1]
auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
bpy.ops.wm.open_mainfile(filepath=auth['blend'])
rigfile=O.parent/'PitViper2011Integration20261002/Single/PitViper2011_single_Editable.blend'
with bpy.data.libraries.load(str(rigfile),link=False) as (a,b):b.objects=['SK_PitViper2011_Manny']
root=b.objects[0].data.bones['WPN_root'].matrix_local.copy()
bpy.data.objects.remove(b.objects[0],do_unlink=True)
ob=bpy.data.objects[auth['name']]
for other in list(bpy.context.scene.objects):
    if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
ob.data.transform(root.inverted())
bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().x<0],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(ob.data);bm.free();ob.data.update()
sys.path.insert(0,str(P/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale([ob]);scene=bpy.context.scene;neutral_output(scene)
lo=Vector([min(v.co[k] for v in ob.data.vertices) for k in range(3)])
hi=Vector([max(v.co[k] for v in ob.data.vertices) for k in range(3)])
center=(lo+hi)/2
bpy.ops.object.camera_add(location=center+Vector((.18,-.040,.006)))
cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=max(hi.y-lo.y,hi.z-lo.z)*1.24;scene.camera=cam
for loc,energy,size in [((.12,-.08,.16),.45,.13),((.1,.13,.03),.25,.10),((-.07,.03,.14),.30,.08)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(loc));lamp=bpy.context.object
    lamp.data.energy=energy;lamp.data.shape='DISK';lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=48
if scene.world is None:scene.world=bpy.data.worlds.new('VIP longitudinal icon neutral studio')
scene.world.color=(.06,.06,.06);scene.render.film_transparent=True
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(O/'Icons/viper-grip-model-gray.png')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'Icons/VipViperGrip_Icon_Editable.blend'))
bpy.ops.render.render(write_still=True)
(O/'icon_source.json').write_text(json.dumps({'source':'actual authored longitudinal side skin',
    'model':auth['blend'],'output':scene.render.filepath,'resolution':1024,
    'purpose':'production UI pictogram; not acceptance rendering','acceptance_rendered':False},indent=2),encoding='utf8')
print('VIP_LONGITUDINAL_ICON_SOURCE_SAVED',flush=True)
