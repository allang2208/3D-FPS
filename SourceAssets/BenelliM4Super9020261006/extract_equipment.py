import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(r'D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006');X=O/'Exports';bpy.ops.wm.open_mainfile(filepath=str(O/'Super90_Gameplay_Editable.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_Super90'];r.animation_data.action=None
for bone in r.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();glove=bpy.data.objects['hardknuckle'];sleeve=bpy.data.objects['sleeve'];shell=bpy.data.objects['12g_12gauge_0']
# The source glove object also includes uncovered arm skin. Keep only the garment surface.
keep={i for i,m in enumerate(glove.data.materials) if m and 'glove_hardknuckle' in m.name}
bm=bmesh.new();bm.from_mesh(glove.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in keep],context='FACES');bm.to_mesh(glove.data);bm.free()
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.hide_render=False;ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
select([r,glove]);bpy.ops.export_scene.fbx(filepath=str(X/'SK_Super90_HardKnuckle.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
# Author actual equipment display/pickup meshes from the source UV surfaces.
static=[]
for source,name in [(glove,'SM_ue_hardknuckle_gloves'),(sleeve,'SM_ue_st6_sleeves'),(shell,'SM_Super90_Casing')]:
 ob=source.copy();ob.data=source.data.copy();s.collection.objects.link(ob);ob.parent=None;ob.modifiers.clear();ob.matrix_world=Matrix.Identity(4);ob.name=name
 if source!=shell:
  # Draw the two pieces closer without rescaling the actual garment.
  for v in ob.data.vertices:v.co.x += -.13 if v.co.x>0 else .13
 center=sum((Vector(c) for c in ob.bound_box),Vector())/8
 ob.data.transform(Matrix.Translation(-center));select([ob]);bpy.ops.export_scene.fbx(filepath=str(X/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE');static.append(ob)
# Editable delivery contains both native garment pieces and their display derivatives.
for ob in static:ob.hide_set(True);ob.hide_render=True
glove.hide_set(True);glove.hide_render=True;sleeve.hide_set(True);sleeve.hide_render=True
r.animation_data.action=bpy.data.actions['A_Super90_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Gameplay_Editable.blend'))
print('SUPER90_EQUIPMENT_EXTRACTED',flush=True)
