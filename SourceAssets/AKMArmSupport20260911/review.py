import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;variant=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(O/variant/f'A_AKM_{variant}_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1000;s.render.resolution_y=700;s.render.resolution_percentage=100
d=bpy.data.cameras.new('Wrist');c=bpy.data.objects.new('Wrist',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.63
# Match the old camera target exactly for reliable before/after comparisons.
import json
p=json.loads((O/'probe.json').read_text())[variant];target=r.matrix_world@Vector(p['H']).lerp(Vector(p['E']),.4);c.location=target+Vector((-.6,.25,.35));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{variant}_after.png');bpy.ops.render.render(write_still=True)
print('AKM_SUPPORT_RENDER_PASS')
