"""Author and save the owned V17 corpse PA; no gameplay or simulation."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
project = Path(u.Paths.project_dir()).resolve()
if project != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project; assets preserved')
SOURCE = '/Game/Monsters/HundredEyedSlag/RagdollGroundV16/PA_HundredEyedSlag_Ground_V16'
DEST = '/Game/Monsters/HundredEyedSlag/RagdollGroundV17/PA_HundredEyedSlag_Ground_V17'
mesh = u.load_asset('/Game/Monsters/HundredEyedSlag/ArticulationV12/SK_HundredEyedSlag_V12')
physics = u.load_asset(DEST) if u.EditorAssetLibrary.does_asset_exist(DEST) else u.EditorAssetLibrary.duplicate_asset(SOURCE, DEST)
if not mesh or not physics:
    raise RuntimeError('Required source assets are unavailable')
result = u.HundredEyedSlagMonster.repair_corpse_physics_asset(mesh, physics)
if not result:
    raise RuntimeError('Corpse physics authoring failed')
if not u.EditorAssetLibrary.save_loaded_asset(result, only_if_is_dirty=False):
    raise RuntimeError('V17 physics package did not save')
row = {'revision': 'RagdollGroundV17', 'project': str(project),
       'source_physics_asset': SOURCE, 'saved_assets': [result.get_path_name()],
       'container_bone': 'RIG_HundredEyedSlag_V1',
       'changes': ['Bind container body and pelvis joint to mesh reference-skeleton root',
                   'Persist authored linear and angular limits in each joint DefaultProfile',
                   'Preserve 16 fitted anatomical bodies, mass settings and disabled self-collision pairs'],
       'mesh_asset_modified': False, 'animation_assets_modified': False,
       'runtime_tested': False, 'pie_started': False}
(OUT / 'physics_installation.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
print('SLAG_V17_PHYSICS_SAVED ' + result.get_path_name(), flush=True)
