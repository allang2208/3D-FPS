import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson715Upgrade20260914/DanWesson715_Upgrade_Editable.blend'))
r=next(o for o in bpy.data.objects if o.type=='ARMATURE')
print('AUTHOR_RIG',r.name,[list(a) for a in r.matrix_world])
for n in ('WPN_root','WPN_Trigger','WPN_Crane','WPN_Cylinder','WPN_Extractor','WPN_Case_0','WPN_SOCKET_Muzzle'):
 print('AUTHOR_REST',n,[list(a) for a in r.data.bones[n].matrix_local],flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Donor/single/SK_DW715_Donor.fbx'))
r=next(o for o in bpy.data.objects if o.type=='ARMATURE');print('IMPORT_RIG',r.name,[list(a) for a in r.matrix_world]);print('IMPORT_BONES',len(r.data.bones),r.data.bones[0].name)
for n in ('WPN_root','WPN_Trigger','WPN_Crane'):
 print('IMPORT_REST',n,[list(a) for a in r.data.bones[n].matrix_local],flush=True)
