"""Retain current mesh/UV/skin; split shell identity and close inspect's bolt."""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006';X=O/'Exports'
sys.path.insert(0,str(O))
from shell_sections import separate_mounted_shell
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_Super90']
parts=[bpy.data.objects['Super90_'+n] for n in ('body','bolt','loading_gate','trigger')]
changed=separate_mounted_shell(parts)
idle=bpy.data.actions['A_Super90_idle'];inspect=bpy.data.actions['A_Super90_inspect']
rig.animation_data.action=idle;rig.animation_data.action_slot=idle.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
closed=rig.pose.bones['WPN_bolt'].matrix_basis.decompose()
rig.animation_data.action=inspect;rig.animation_data.action_slot=inspect.slots[0]
frames=list(range(round(inspect.frame_range[0]),round(inspect.frame_range[1])+1));rows=[]
for frame in frames:
    scene.frame_set(frame);bpy.context.view_layer.update()
    row={b.name:b.matrix_basis.decompose() for b in rig.pose.bones}
    row['WPN_bolt']=tuple(v.copy() for v in closed);rows.append(row)
sys.path.insert(0,str(O.parent/'M1911RevolverInspect20260927'))
import author_support as support
support.DURATION=(frames[-1]-frames[0])/60
support.bake_action(rig,scene,'A_Super90_inspect',rows,frames)

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=rig

select([rig])
bpy.ops.export_scene.fbx(filepath=str(X/'A_Super90_inspect.fbx'),use_selection=True,
    object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
select([rig]+parts+[bpy.data.objects['12g_12gauge_0']]+[
    ob for ob in scene.objects if ob.type=='MESH' and ob.name.startswith('Super90_V7_')])
bpy.ops.export_scene.fbx(filepath=str(X/'SK_Super90_V7.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
rig.animation_data.action=idle;rig.animation_data.action_slot=idle.slots[0]
scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_ShellMechanics_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'mesh':str(X/'SK_Super90_V7.fbx'),
    'inspect':str(X/'A_Super90_inspect.fbx'),'mounted_faces':changed,
    'mounted_slot':'12gauge_mounted','loose_slot':'12gauge','inspect_frames':len(frames),
    'runtime_tested':False},indent=2),encoding='utf-8')
print('SUPER90_SHELL_MECHANICS_AUTHORED',changed,flush=True)
