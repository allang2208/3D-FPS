"""Save repaired gun shading and export the current complete native viewmodel."""
import bpy,json,shutil,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
sys.path.insert(0,str(O));from surface_normals import repair_gun_normals
B=O/'Before';B.mkdir(exist_ok=True)
editable=S/'Super90_Gameplay_Editable.blend';file=S/'Exports/SK_Super90_V7.fbx'
for p in (editable,file):
    if not (B/p.name).exists():shutil.copy2(p,B/p.name)
bpy.ops.wm.open_mainfile(filepath=str(editable));s=bpy.context.scene;r=bpy.data.objects['SK_Super90']
action=r.animation_data.action;slot=r.animation_data.action_slot;frame=s.frame_current
r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
parts=[bpy.data.objects['Super90_'+n] for n in ('body','bolt','loading_gate','trigger')]
receipt={'parts':repair_gun_normals(parts),'mesh_export':str(file),'runtime_tested':False}
# Keep the authored texture, reducing the large baked slope contribution.
m=bpy.data.materials['TTI_Benelli_M4']
for n in m.node_tree.nodes:
    if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.5
objects=[r]+parts+[bpy.data.objects['12g_12gauge_0']]+[o for o in s.objects if o.type=='MESH' and o.name.startswith('Super90_V7_')]
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
r.animation_data.action=action
if slot:r.animation_data.action_slot=slot
s.frame_set(frame)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(editable))
(O/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SUPER90_SURFACE_EXPORTED',flush=True)
