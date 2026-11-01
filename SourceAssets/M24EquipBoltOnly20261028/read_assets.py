import unreal as u,json,hashlib,ast
from pathlib import Path
O=Path(__file__).resolve().parent
node=next(n for n in ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='packed');exec(compile(ast.unparse(node),'pack','exec'))
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
equip='/Game/Weapons/M24/MotionMagazine20261027/Animations/A_M24_equip'
def digest(p):return hashlib.sha256((Path(u.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'profiles':{f:packed(u.load_asset(p),f) for f,p in paths.items()},'equip':{'path':equip,'sha256':digest(equip)},'world':world.get_path_name() if world else None,'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
(O/'before.json').write_text(json.dumps(result));print('M24_EQUIP_INPUTS',json.dumps({'world':result['world'],'dirty':result['dirty'],'equip':result['equip']}),flush=True)
