import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Foregrip_Pose.blend'))
ob=bpy.data.objects['FG_Frame_M4Body'];assert len(ob.data.vertices)==40
inner=[(-.43,.31),(.65,.31),(.77,.24),(.76,.12),(.64,-.025),(.28,-.54),(.015,-.54),(-.11,-.28),(-.32,.10),(-.41,.20)]
for start in [10,30]:
 for i,(x,z) in enumerate(inner):ob.data.vertices[start+i].co.x=x;ob.data.vertices[start+i].co.z=z
ob.data.update()
G=Matrix(json.loads((O/'fit_pose.json').read_text())['grip_matrix'])
for part in bpy.context.scene.objects:
 if part.name.startswith(('FG_DecorativeFastener','FG_FastenerInset')) and abs((G.inverted()@part.location).z+.53)<.01:part.location+=G.to_3x3()@Vector((0,0,-.06))
 if part.name.startswith('FG_SupportInset'):part.location+=G.to_3x3()@Vector((.04,0,0))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Foregrip_Fitted.blend'))
