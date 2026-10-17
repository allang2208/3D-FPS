"""Read-only saved-asset audit. No saves, particle simulation or screenshots."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import emitters

rows = []
for name in ('NS_FlameArmorBodyV2', 'NS_FlameArmorWeaponV2', 'NS_FlameArmorArrowV2'):
    path = '/Game/Skills/FlameArmor20261016/TorchV2/' + name
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing saved flame system: ' + path)
    rows.append({'asset': path, 'emitters': emitters(asset)})
assert set(rows[0]['emitters']) == {'FootRingV4', 'FootRingEmbersV4'}, rows[0]
assert rows[1]['emitters'] and rows[2]['emitters']
out = {'passed': True, 'body_ring_only': True, 'systems': rows, 'rendered': False}
(ROOT / 'SourceAssets/FlameArmor20261017/NetworkAudit/assets.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('FLAME_ARMOR_ASSET_AUDIT', json.dumps(out))
