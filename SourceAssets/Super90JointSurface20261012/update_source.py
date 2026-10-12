"""Save an independently editable native surface; no animation export."""
import bpy,sys,json,hashlib,shutil
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006';P=O.parents[1]
sys.path.insert(0,str(O));from blender_surface import apply_to_blender
def backup(file):
 target=O/'Before'/file.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():shutil.copy2(file,target)
source=S/'Super90_Gameplay_Editable.blend';backup(source)
bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects['SK_Super90'];scene=bpy.context.scene
arms=[o for o in scene.objects if o.type=='MESH' and o.name.startswith('Super90_V7_')]
arms=apply_to_blender(arms,rig)
frame=scene.frame_current;action=rig.animation_data.action;slot=rig.animation_data.action_slot
rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
scene.frame_set(0);bpy.context.view_layer.update()
parts=[bpy.data.objects['Super90_'+n] for n in ('body','bolt','loading_gate','trigger')]+[bpy.data.objects['12g_12gauge_0']]
receipt={'editable':str(source),'exports':[],'animation_exported':False,'weights_edited':False}
for label,objects in [('SK_Super90_V7',parts+arms),('SK_Super90_BareArmsV7',arms)]:
 target=S/'Exports'/(label+'.fbx');backup(target)
 bpy.ops.object.select_all(action='DESELECT')
 for ob in [rig]+objects:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 receipt['exports'].append({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
rig.animation_data.action=action;rig.animation_data.action_slot=slot;scene.frame_set(frame)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(source))
receipt['editable_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
(O/'source_saved.json').write_text(json.dumps(receipt,indent=2));print('SUPER90_SOURCE_SAVED')
