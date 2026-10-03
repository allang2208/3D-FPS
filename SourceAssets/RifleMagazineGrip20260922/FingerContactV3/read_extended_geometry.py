"""Read the AKM extension in the same magazine-local frame as the grasp."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'AKMReloadPolish20260911/base/A_AKM_reload.blend'))
r=bpy.data.objects['SK_M4_Infima'];xf=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()@r.matrix_world.inverted()
bpy.ops.wm.read_factory_settings(use_empty=True)
source=S/'ExtMagContinuity20260919/FBX/SM_ExtMag_AKM40_Continuous.fbx'
bpy.ops.import_scene.fbx(filepath=str(source));vertices=[];faces=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    offset=len(vertices);vertices.extend([list(xf@ob.matrix_world@v.co) for v in ob.data.vertices])
    faces.extend([[offset+i for i in p.vertices] for p in ob.data.polygons])
(O/'extra_magazines.json').write_text(json.dumps({'AKM_extended':{'vertices':vertices,'faces':faces,'source':str(source)}}))
print('AKM_EXTENSION_GEOMETRY_READ',len(vertices),len(faces),flush=True)
