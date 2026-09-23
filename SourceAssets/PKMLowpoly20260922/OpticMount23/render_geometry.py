"""Requested connector inspection: authoring geometry only, no game startup."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_OpticMount_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit
new=[o for o in bpy.context.scene.objects if o.get('PKM23_part')]
with bpy.data.libraries.load(str(R/'Accessories14/SM_PKM_optic_rail.blend'),link=False) as (a,b):b.objects=a.objects
old=[o for o in b.objects if o and o.type=='MESH']
for o in old:bpy.context.scene.collection.objects.link(o);o.matrix_world=B@Matrix.Translation((0,-.021,.070));o.hide_render=True
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO'
s.display.shading.color_type='SINGLE';s.display.shading.single_color=(.24,.27,.30)
s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world.color=(.06,.06,.06)
s.render.resolution_x=1400;s.render.resolution_y=950;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
camdata=bpy.data.cameras.new('MountInspection');cam=bpy.data.objects.new('MountInspection',camdata);s.collection.objects.link(cam)
cam.location=B@Vector((.285,.255,.235));target=B@Vector((0,.083,.10))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=.29;s.camera=cam
for version in ['before','after']:
 for o in old:o.hide_render=version!='before'
 for o in new:o.hide_render=version!='after'
 s.render.filepath=str(O/('mount_'+version+'.png'));bpy.ops.render.render(write_still=True)
