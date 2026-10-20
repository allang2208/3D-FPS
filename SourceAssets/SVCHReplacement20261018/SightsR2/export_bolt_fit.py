"""Bake a per-part bind correction into export copies, preserving editable art."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SVCH_SightsR2_Editable.blend'),load_ui=False)
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST'
d=json.loads((O/'bolt_fit_recipe.json').read_text())['delta_component_cm'];shift=Vector((d[0]*.01,-d[1]*.01,d[2]*.01));copies=[];count=0
for ob in list(bpy.context.scene.objects):
 if ob.type!='MESH':continue
 clone=ob.copy();clone.data=ob.data.copy();bpy.context.scene.collection.objects.link(clone);copies.append(clone)
 group=clone.vertex_groups.get('WPN_bolt')
 if group:
  local=clone.matrix_world.inverted().to_3x3()@shift
  for v in clone.data.vertices:
   if any(g.group==group.index and g.weight>.999 for g in v.groups):v.co+=local;count+=1
assert count==857
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();combined=bpy.context.object;combined.name='SVCH_SightsR2_BoltFit';rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_SVCH_SightsR2_BoltFit.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
print('SVCH_BOLT_BIND_EXPORT_SAVED',count,flush=True)
