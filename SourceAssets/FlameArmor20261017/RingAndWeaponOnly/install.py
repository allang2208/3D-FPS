"""Remove only the upper-body emitters; preserve current foot and weapon assets."""
import importlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/FlameArmor20261017/RingAndWeaponOnly'
BODY = '/Game/Skills/FlameArmor20261016/TorchV2/NS_FlameArmorBodyV2'
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
import author_flame_armor_fireball_v3 as author
importlib.reload(author)
if BODY in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve unsaved flame armor system: ' + BODY)
source = ROOT / 'Content/Skills/FlameArmor20261016/TorchV2/NS_FlameArmorBodyV2.uasset'
backup = OUT / 'Before' / source.name
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(source, backup)
system = u.load_asset(BODY)
removed = author.remove_body_layers(system)
author.base.save(system)
receipt = {'saved_asset': system.get_path_name(), 'removed_emitters': removed,
           'foot_ring_modified': False, 'weapon_modified': False, 'native_cpp_changed': False,
           'runtime_tested': False, 'backup': str(backup)}
(OUT / 'delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('FLAME_ARMOR_RING_WEAPON_ONLY_SAVED', json.dumps(receipt))
