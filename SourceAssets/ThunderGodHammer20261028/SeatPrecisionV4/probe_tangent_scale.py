import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'ThorSeatsPrecisionV4.blend'))
src=bpy.data.objects['SM_ThunderGodHammer_head_mount_factory'].data
for scale in [1,100]:
 m=src.copy()
 for v in m.vertices:v.co*=scale
 m.update();m.calc_tangents(uvmap=m.uv_layers[0].name)
 print('TANGENT_SCALE',scale,sum(l.tangent.length<1e-4 or l.bitangent.length<1e-4 for l in m.loops),flush=True)
