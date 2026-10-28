"""Apply the user's revised strong-draw effects to the current shared bow catalog."""
from pathlib import Path
from datetime import datetime
import hashlib, json, os

P = Path(__file__).parent
ROOT = Path('D:/FPS3D/FPSGAME')
path = ROOT / 'Content/ColdSteelData/bow-gunsmith.json'
raw = path.read_bytes()
data = json.loads(raw)
riser = next(column for column in data['columns'] if column['key'] == 'riser')
part = next(option for option in riser['options'] if option['id'] == 'strong_draw')
before = json.loads(json.dumps(part, ensure_ascii=False))
stats = part['stats']
for key in ('damage_mult', 'shot_damage_mult', 'draw_mult', 'draw_speed_bonus', 'piercing_charge_speed_bonus'):
    stats.pop(key, None)
stats.update(physical_damage_mult=1.05, piercing_damage_mult=1.30,
             stamina_mult=1.50, charge_stamina_mult=1.50)
part['special_effects'] = ['穿心蓄势｜学会穿心箭后，满拉并蓄力至穿心就绪，穿心箭伤害 +30%。']
out = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup = P / ('Before-' + stamp)
backup.mkdir()
(backup / path.name).write_bytes(raw)
temp = path.with_name(path.name + '.strong-draw-v7.tmp')
temp.write_bytes(out)
if path.read_bytes() != raw:
    raise RuntimeError('Preserving a concurrent bow catalog edit; source and backup retained.')
os.replace(temp, path)
receipt = {'applied_at': datetime.now().isoformat(), 'catalog': str(path),
           'backup': str(backup / path.name), 'before': before, 'after': part,
           'catalog_sha256': hashlib.sha256(out).hexdigest(),
           'speed_rule': 'One shared draw-speed factor for full draw and heart-piercing readiness.',
           'gameplay_tested': False}
(P / ('catalog-receipt-' + stamp + '.json')).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('STRONG_DRAW_V7_INSTALLED ' + str(path), flush=True)
