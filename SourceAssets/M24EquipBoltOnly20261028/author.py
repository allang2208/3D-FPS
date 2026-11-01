"""Keep only the final bolt cycle from the authored M24 equip action."""
import bpy,json,ast
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent;previous=O.parent/'M24MagazineGraspEquip20261028'
bpy.ops.wm.open_mainfile(filepath=str(previous/'M24_GraspEquip_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];s=bpy.context.scene
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
rest={n:Matrix(m) for n,m in source['rest'].items()};parents=source['parents']
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
data=json.loads((previous/'final_poses.json').read_text())
# Old source 48..106 already contains the small idle-to-bolt entry blend and
# ends at the exact hip idle. No magazine seat or raise is included.
rows=[{n:Matrix(m) for n,m in row.items()} for row in data['equip'][48:107]]
report={'clips':{},'previous_source_frames':[48,106],'source_fps':30,'charge_pull':25/30,'charge_release':40/30,'runtime_tested':False}
node=next(n for n in ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'bake','exec'))
node=next(n for n in ast.parse((O.parent/'M24MotionMagazine20261027/author.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='export');exec(compile(ast.unparse(node),'export','exec'))
for role in ('equip_mag10','equip'):
 r.animation_data_clear();old=bpy.data.actions.get('A_M24_'+role)
 if old:bpy.data.actions.remove(old)
 bake(role,rows)
folder=O/'Export';folder.mkdir(exist_ok=True);path=folder/'A_M24_equip.fbx';export(path,[r],True)
report['clips']['equip']['file']=str(path)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_EquipBoltOnly_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('M24_EQUIP_BOLT_ONLY_AUTHORED',flush=True)
