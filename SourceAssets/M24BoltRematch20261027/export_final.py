import bpy,json,ast
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent
exec(compile((O/'author_candidate.py').read_text().split("roles=('fire'")[0],'setup','exec'))
clips={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((O/'refined_poses.json').read_text()).items()}
tree=ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
report={'clips':{},'fps':30,'source':'M24CustomScope20261026/Donor/Source/source/arms@sniper.fbx','runtime_tested':False}
exec(compile(ast.unparse(node),'bake','exec'))
X=O/'Exports';X.mkdir(exist_ok=True)
owned=[n for n in rest if under(n,'clavicle_r')]
for role,rows in clips.items():
 old=bpy.data.actions['A_M24_'+role];r.animation_data.action=None;bpy.data.actions.remove(old);bake(role,rows)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 path=X/('A_M24_'+role+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 report['clips'][role].update(file=str(path),owned_bones=owned)
r.animation_data.action=bpy.data.actions['A_M24_fire'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(29)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_BoltRematch_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
