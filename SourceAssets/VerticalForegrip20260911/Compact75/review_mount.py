import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'Compact_Baseline.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];G=Matrix(json.loads((O/'fit_baseline.json').read_text())['grip_matrix'])
for ob in s.objects:ob.hide_render=not(ob.name.startswith('VG_') or ob.name=='M4_Handguard Kmode Unreal_Export')
d=bpy.data.cameras.new('MountReview');cam=bpy.data.objects.new('MountReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.10;d.clip_start=.001;focus=G@Vector((0,0,-.005))
for pos in [(0,-.2,.2),(.2,.2,.1)]:
 d=bpy.data.lights.new('MountLight','AREA');d.energy=10;d.size=.3;o=bpy.data.objects.new('MountLight',d);s.collection.objects.link(o);o.location=focus+Vector(pos);o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100
for label,offset in [('side',(0,-.2,.02)),('front',(.2,0,.005))]:
 cam.location=focus+G.to_3x3()@Vector(offset);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'mount_{label}.png');bpy.ops.render.render(write_still=True)
