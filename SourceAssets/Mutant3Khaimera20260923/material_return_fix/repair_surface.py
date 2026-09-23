"""Rebuild and persist Mutant3's source-to-render material binding, without running a game."""
from pathlib import Path
import json
import unreal as u

ROOT = Path(__file__).parent
ASSET = '/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw'
if Path(u.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected project')
mesh = u.load_asset(ASSET)
if not mesh:
    raise RuntimeError('Mutant3 production mesh is missing')
if not u.Mutant3.repair_surface_binding(mesh):
    raise RuntimeError('Mutant3 source/render surface repair did not complete; asset not saved')
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('Mutant3 rebuilt mesh save failed')
report = {
    'asset': ASSET,
    'state': 'source slot names, imported sections and render data rebuilt; asset saved',
    'material': '/Game/Monsters/Mutant3Meshy/Materials/M_Mutant3_Meshy',
    'material_slot': 0,
    'game_started': False,
    'animation_or_physics_modified': False,
}
(ROOT/'surface_saved.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MUTANT3_SURFACE_SAVED '+json.dumps(report))
