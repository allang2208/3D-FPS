"""Write the same objects, bindings, UVs and faces with refined vertex data."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;(O/'Exports').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
records=json.loads((O/'source.json').read_text());rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear();rig.data.pose_position='REST'
for item in records:
 path=O/'Work'/(item['object']+'_edited.npz')
 if not path.exists():continue
 ob=bpy.data.objects[item['object']];me=ob.data;data=np.load(path);matrix=Matrix(item['matrix']);inverse=matrix.inverted()
 for v,p in zip(me.vertices,data['vertices']):v.co=inverse@Vector(p)
 norms=[(matrix.to_3x3().transposed()@Vector(n)).normalized() for n in data['normals']]
 me.update();me.normals_split_custom_set(norms)
 ob['Surface32']='Original topology/UV/rig; locally faired fitted vertices; no added geometry'
for mat in bpy.data.materials:
 if not mat.name.startswith('M_LMG201_') or not mat.use_nodes:continue
 for node in mat.node_tree.nodes:
  if node.type!='TEX_IMAGE' or not node.image:continue
  for kind in ['BaseColor','ORM']:
   if 'Surface_'+kind in node.image.name:
    im=bpy.data.images.load(str(O/'Textures'/('T_LMG201_S32_'+kind+'.png')),check_existing=True);im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';node.image=im
 bs=mat.node_tree.nodes.get('Principled BSDF')
 if bs:bs.inputs['Specular IOR Level'].default_value=.28
 if bs and 'Interior' in mat.name:bs.inputs['Roughness'].default_value=.76;bs.inputs['Metallic'].default_value=.20
 if bs and 'Steel' in mat.name:bs.inputs['Roughness'].default_value=.56;bs.inputs['Metallic'].default_value=.65
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def fbx(file,obs,rigged=False):
 select(obs);bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'} if rigged else {'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
exports={}
for key,name in [('FrontSight','FrontSight_Fitted'),('RearSight','RearSight')]:
 ob=bpy.data.objects[name];transform=ob.matrix_world.copy();ob.matrix_world=Matrix.Identity(4)
 file=O/'Exports'/('SM_LMG201_S32_'+key+'.fbx');fbx(file,[ob]);exports[key]=str(file);ob.matrix_world=transform
body=[bpy.data.objects[i['object']] for i in records if i['object'] not in ['FrontSight_Fitted','RearSight']]
copies=[]
for ob in body:
 cp=ob.copy();cp.data=ob.data.copy();bpy.context.scene.collection.objects.link(cp);copies.append(cp)
select(copies);bpy.ops.object.join();joined=bpy.context.object;joined.name='LMG201_S32_OriginalSurface'
file=O/'Exports/SK_LMG201_S32_Weapon.fbx';fbx(file,[joined,rig],True);exports['Weapon']=str(file);bpy.data.objects.remove(joined,do_unlink=True)
for im in bpy.data.images:
 if im.name.startswith('T_LMG201_S32_'):im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_S32_Editable.blend'))
(O/'exports.json').write_text(json.dumps({'exports':exports,'material_roles':json.loads((O.parent/'Install30/fit.json').read_text())['material_roles'],'source':'Install30/LMG201_R30_NativeFit.blend','topology_changed':False,'new_components':0},indent=2))
print('S32_EXPORTED',exports,flush=True)
