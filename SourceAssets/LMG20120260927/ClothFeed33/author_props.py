"""Rig the existing R30 cloth pouch and segmented belt; retain their UVs."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;(O/'Exports').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear();rig.data.pose_position='REST'
root=rig.data.bones['WPN_root'].matrix_local.copy();exports=[];roles={};centers=[]
# Six visible cartridges on the regenerated model. Each cartridge stays rigid;
# only the narrow connector regions interpolate between adjacent segments.
belt=bpy.data.objects['AmmoBelt'];zlo=min(v.co.z for v in belt.data.vertices);zhi=max(v.co.z for v in belt.data.vertices)
pitch=(zhi-zlo)/6
for i in range(6):centers.append([.03835,.1382,zhi-pitch*(i+.5)])
for prefix in ('Old','New'):
 for part in ('AmmoBag','AmmoBelt'):
  src=bpy.data.objects[part];ob=src.copy();ob.data=src.data.copy();bpy.context.scene.collection.objects.link(ob)
  ob.name='Cloth33_'+prefix+part;ob.hide_set(False);ob.hide_render=False
  ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
  normals=[root.to_3x3()@n.vector for n in ob.data.corner_normals]
  local=[v.co.copy() for v in ob.data.vertices];ob.data.transform(root);ob.data.normals_split_custom_set(normals)
  ob.vertex_groups.clear();boneprefix='New_' if prefix=='New' else ''
  if part=='AmmoBag':ob.vertex_groups.new(name=boneprefix+'LMG201_Box').add(list(range(len(local))),1.,'REPLACE')
  else:
   groups=[ob.vertex_groups.new(name=boneprefix+'LMG201_Belt_%02d'%i) for i in range(6)]
   for vi,p in enumerate(local):
    slot=max(0,min(5,int((zhi-p.z)/pitch)));groups[slot].add([vi],1.,'REPLACE')
    # Blend only vertices at the link boundaries, never the cartridge centers.
    boundary=round((zhi-p.z)/pitch);distance=(zhi-p.z)-boundary*pitch
    if 0<boundary<6 and abs(distance)<.00065:
     for g in groups:g.remove([vi])
     w=.5+.5*distance/.00065
     groups[boundary-1].add([vi],1-w,'REPLACE');groups[boundary].add([vi],w,'REPLACE')
  for i,mat in enumerate(list(ob.data.materials)):
   role='Cloth' if part=='AmmoBag' else 'Interior' if 'Interior' in mat.name else 'Belt'
   key='M_LMG201_Cloth33__'+prefix+('Box' if part=='AmmoBag' else 'Belt')+'_'+role
   dest=bpy.data.materials.get(key)
   if not dest:dest=mat.copy();dest.name=key
   ob.data.materials[i]=dest;roles[key]=role
  ob.modifiers.new('Cloth33_NativeRig','ARMATURE').object=rig;exports.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in exports:ob.select_set(True)
rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=O/'Exports/SK_LMG201_Cloth33_Props.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Cloth33_Editable.blend'))
(O/'props.json').write_text(json.dumps({'fbx':str(fbx),'roles':roles,'belt_centers_root_ue':centers,'pouch_contact_root_ue':[.066,.131,-.06],'cover_open_contact_root_ue':[.018,.113,.080],'cover_close_contact_root_ue':[.010,.158,.083],'source':'Install30/LMG201_R30_NativeFit.blend','new_geometry_created':False,'existing_skeleton_extended':False},indent=2))
print('CLOTH33_PROPS_EXPORTED',str(fbx),flush=True)
