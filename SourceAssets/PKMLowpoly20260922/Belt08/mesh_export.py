"""Export one bound assembly, retaining independent editable source pieces."""
import bpy

def align_export_uvs(mesh):
 """Join by channel role, not source names (DiffuseUV / PKM_QBZ_SurfaceUV).

 Blender unions UV layers by name when joining. Without this mapping the
 Manny hands end up with zero UV0 and valid UVs only in UV1. Every material
 in this assembly samples its primary texture/mask from TexCoord0.
 Operate on export copies only; retain additional UV channels in order.
 """
 if not mesh.uv_layers:return
 primary=next((layer for layer in mesh.uv_layers if layer.active_render),mesh.uv_layers.active)
 layers=[primary]+[layer for layer in mesh.uv_layers if layer!=primary]
 channels=[]
 for layer in layers:
  data=[0.]*(len(mesh.loops)*2);layer.data.foreach_get('uv',data);channels.append(data)
 for layer in list(mesh.uv_layers):mesh.uv_layers.remove(layer)
 for index,data in enumerate(channels):
  layer=mesh.uv_layers.new(name='PKM_ExportUV'+str(index))
  layer.data.foreach_set('uv',data);layer.active_render=index==0
 mesh.uv_layers.active_index=0

def export_mesh(r,path):
 scene=bpy.context.scene
 objects=[o for o in scene.objects if o.type=='MESH' and (o.name=='SK_Manny_Arms_Export' or 'mechanical_bone' in o)]
 prior=r.data.pose_position;r.data.pose_position='REST';bpy.context.view_layer.update()
 bpy.ops.object.select_all(action='DESELECT');copies=[]
 for original in objects:
  ob=original.copy();ob.data=original.data.copy();scene.collection.objects.link(ob)
  ob.name='PKM08_ExportPart';ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
  # Preserve existing per-part bevels/normals before joining the export copy.
  for modifier in list(ob.modifiers):
   if modifier.type!='ARMATURE':bpy.ops.object.modifier_apply(modifier=modifier.name)
  align_export_uvs(ob.data)
  copies.append(ob)
 bpy.context.view_layer.objects.active=copies[-1];bpy.ops.object.join();assembly=bpy.context.object;assembly.name='PKM08_ExportAssembly'
 r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',path_mode='AUTO')
 bpy.data.objects.remove(assembly,do_unlink=True);r.data.pose_position=prior;bpy.context.view_layer.update()

if __name__=='__main__':
 from pathlib import Path
 O=Path(__file__).parent
 bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Gameplay_Editable.blend'))
 export_mesh(bpy.data.objects['PKM_Manny_Rig'],O/'Exports/SK_PKM_Manny.fbx')
 print('BELT08_SINGLE_ASSEMBLY_EXPORTED',flush=True)
