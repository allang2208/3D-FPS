"""Create the same native mesh with separate material identities for WS1."""
import bpy,json,shutil,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006';B=O/'Before';B.mkdir(exist_ok=True);X=O/'Exports';X.mkdir(exist_ok=True)
sys.path.insert(0,str(O));from surface_regions import apply_surface_regions,ROLES
src=S/'Super90_Gameplay_Editable.blend'
if not (B/src.name).exists():shutil.copy2(src,B/src.name)
bpy.ops.wm.open_mainfile(filepath=str(src));s=bpy.context.scene;r=bpy.data.objects['SK_Super90']
parts=[bpy.data.objects['Super90_'+n] for n in ('body','bolt','loading_gate','trigger')]
report=apply_surface_regions(parts)
sys.path.insert(0,str(O.parent/'Super90ShellMechanics20261008'))
from shell_sections import separate_mounted_shell
report['mounted_shell_sections']=separate_mounted_shell(parts)
from mapping import correct_weapon_uv,VERSION
correct_weapon_uv([bpy.data.objects['12g_12gauge_0']])
action=r.animation_data.action;slot=r.animation_data.action_slot;frame=s.frame_current;r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT')
for ob in [r]+parts+[bpy.data.objects['12g_12gauge_0']]+[o for o in s.objects if o.type=='MESH' and o.name.startswith('Super90_V7_')]:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=r
file=X/'SK_Super90_V7.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
r.animation_data.action=action;r.animation_data.action_slot=slot;s.frame_set(frame)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_WS1_Editable.blend'))
report.update({'mesh_fbx':str(file),'master':'/Game/Weapons/WeaponSurface/Master/M_WeaponSurface','source':str(src),'runtime_tested':False,'recipe':{n:{'preset':p,'color':c,'roughness':rough,'metallic':m} for n,(p,c,rough,m) in ROLES.items()}})
report['atlas_mapping']=VERSION
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_WS1_SURFACES_AUTHORED',json.dumps(report['slots']),flush=True)
