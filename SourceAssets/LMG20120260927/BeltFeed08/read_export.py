import bpy,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/BeltFeed08')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'PKM_Installed_Donor.fbx'),use_anim=False)
for ob in bpy.data.objects:
 if ob.type=='ARMATURE':
  print('RIG',ob.name,'matrix',list(map(list,ob.matrix_world)),flush=True)
  for n in ['WPN_root','hand_l','PKM_Cover','PKM_Box','PKM_Belt_00']:
   if n in ob.data.bones:print('BONE',n,'matrix',list(map(list,ob.data.bones[n].matrix_local)),flush=True)
 if ob.type=='MESH':print('MESH',ob.name,len(ob.data.vertices),[m.name for m in ob.data.materials],flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_Installed_Donor.blend'))