"""Prepare/save the existing hit bodies for ranged queries and death simulation."""
import json
from pathlib import Path
import unreal as u

mesh = u.load_asset('/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy')
# The native authoring entry logs the stored flags and constraints before editing.
if not u.FatZombie.prepare_combat_physics(mesh, True):
    raise RuntimeError('Cannot prepare fat zombie combat physics')
physics = mesh.get_editor_property('physics_asset')
u.EditorAssetLibrary.set_metadata_tag(physics, 'Purpose',
    'Simple+complex bone hit queries; 18 fitted bodies plus non-contact root; constrained death ragdoll')
if not u.EditorAssetLibrary.save_loaded_asset(physics, False):
    raise RuntimeError('Cannot save fat zombie combat physics')
out = Path('D:/FPS3D/FPSGAME/Saved/FatZombieRangedRagdoll')
out.mkdir(parents=True, exist_ok=True)
(out / 'asset_prepared.json').write_text(json.dumps({
    'mesh': mesh.get_path_name(), 'physics': physics.get_path_name(),
    'body_shapes': 'Original fitted capsules retained; non-contact root added',
    'trace_mode': 'CTF_UseSimpleAsComplex', 'body_mode': 'PhysType_Default',
    'runtime_tested': False
}, indent=2), encoding='utf-8')
u.log('FAT_COMBAT_PHYSICS_SAVED ' + physics.get_path_name())
