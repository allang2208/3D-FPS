"""Export only Bellow's current living surface for the standard continuous corpse pipeline."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/SoftDeathV08')
DEST = '/Game/Monsters/BellowSacLobber/V08/SoftDeath'
KEY = 'BellowSacLobber'
E = u.EditorAssetLibrary
ROOT.mkdir(parents=True, exist_ok=True)
out = ROOT / KEY
out.mkdir(exist_ok=True)
bp = u.load_asset('/Game/Monsters/BellowSacLobber/BP_BellowSacLobber')
cdo = u.get_default_object(bp.generated_class())
animation_set = cdo.get_editor_property('animation_set')
mesh = animation_set.get_editor_property('reference_mesh')
if not mesh:
    raise RuntimeError('Current Bellow animation set has no living mesh')
corpse_path = DEST + '/SK_BellowSacLobber_SoftCorpse'
data = u.load_asset(DEST + '/DA_BellowSacLobber_SoftCorpse')
corpse = u.load_asset(corpse_path) or E.duplicate_asset(mesh.get_path_name(), corpse_path)
already_bound = data and data.get_editor_property('corpse_mesh') == corpse
if already_bound:
    if not (out / 'surface.bin').exists():
        raise RuntimeError('Original export missing; do not export an already rebound corpse')
else:
    if not u.M14SoftBodyData.export_surface(corpse, str(out / 'surface.bin'), []):
        raise RuntimeError('Bellow source export failed')
    if not E.save_loaded_asset(corpse, False):
        raise RuntimeError('Bellow corpse source could not be saved')
item = dict(key=KEY, characters=[KEY], source=mesh.get_path_name(), corpse=corpse_path,
            skeleton=mesh.skeleton.get_path_name(), blueprint=bp.get_path_name(),
            animation_set=animation_set.get_path_name(), omitted_attack_branches=[], tested=False)
(ROOT / 'sources.json').write_text(json.dumps([item], ensure_ascii=False, indent=2), encoding='utf-8')
print('BELLOW_SOFT_DEATH_V08_EXPORTED ' + mesh.get_path_name())
