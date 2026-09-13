"""Export compact skinned nodes while keeping editable components separate."""
import bpy,json
from pathlib import Path

def export_joined(rig,hands,objects,out):
 copies=[]
 for ob in objects:
  if ob.name=='QBZ_Magazine':continue
  copy=ob.copy();copy.data=ob.data.copy();bpy.context.scene.collection.objects.link(copy);copy.hide_set(False);copies.append(copy)
 bpy.ops.object.select_all(action='DESELECT')
 for ob in copies:ob.select_set(True)
 bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();gun=bpy.context.object;gun.name='QBZ191_Hero_Export'
 magazine=next(ob for ob in objects if ob.name=='QBZ_Magazine')
 bpy.ops.object.select_all(action='DESELECT')
 for ob in [rig,hands,gun,magazine]:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.fbx(filepath=str(out/'SK_QBZ191_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 bpy.data.objects.remove(gun,do_unlink=True)

if __name__=='__main__':
 O=Path(__file__).parent
 bpy.ops.wm.open_mainfile(filepath=str(O/'QBZ191_Hero_Editable.blend'))
 rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';bpy.context.view_layer.update()
 names=[n for group in json.loads((O/'textures.json').read_text()).values() for n in group['objects'] if not n.startswith('SM_QBZ191_')]
 export_joined(rig,bpy.data.objects['SK_Manny_Arms_Export'],[bpy.data.objects[n] for n in names],O)
 print('QBZ_HERO_COMPACT_EXPORT_COMPLETE',flush=True)
