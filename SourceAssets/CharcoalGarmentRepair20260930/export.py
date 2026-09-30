import sys
from pathlib import Path
import bpy
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/CharcoalGarmentRepair20260930'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from render_field_sweater_inventory_icons import garment,material,read
for profile in ['Body','Traversal']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 d=read(R/'Authored'/(profile+'.json'))
 obj=garment(d,'Charcoal_'+profile,[material('Charcoal',i,(.045,.053,.065),True) for i in range(3)])
 for bone in obj.parent.pose.bones:bone.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update();obj.parent['NativeReferencePose']=True
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/(profile+'.blend')))
 if profile=='Body':
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bpy.ops.export_scene.fbx(filepath=str(R/'SM_Charcoal_Garment.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,apply_unit_scale=True,bake_anim=False)
print('CHARCOAL_EDITABLE_EXPORT_DONE',flush=True)
