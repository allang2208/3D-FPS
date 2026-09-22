"""Register the SVD in the ColdSteel data files (items / gunsmith / damage formulas).

Each file is rewritten with its own conventions (2-space indent, keep-insertion-order,
non-ASCII kept literal, trailing newline). Run with --check to only report what would change.

    python register_svd_data.py [--check]
"""
import json
import sys
from pathlib import Path

DATA = Path(r'D:\FPS3D\FPSGAME\Content\ColdSteelData')
CHECK = '--check' in sys.argv

ITEM = {
    "category": "weapon",
    "desc": "冷战年代定型的半自动狙击步枪，长枪管配 7.62×54R 有底缘弹，出厂即带 PSO-1 四倍镜，"
            "镜筒偏置在机匣左侧，配骨架式枪托与十发弹匣。单发威力足，后坐偏重，射速受扳机限制，"
            "适合架住中远距离逐发放倒目标；近距离缠斗时换弹偏慢，必须留出退弹的余地。",
    "equipSlot": "weapon",
    "icon": "Icons/ue_svd.png",
    "ue_icon": "Icons/ue_svd.png",
    "id": "ue_svd",
    "isTwoHanded": True,
    "name": "SVD",
    "rarity": "common",
    "stack_max": 1,
    "stats": [
        {"name": "物理攻击", "value": "65"},
        {"name": "弹匣容量", "value": "10"},
    ],
    "type": "武器",
    "weaponType": "rifle",
}

WEAPON = {
    "id": "ue_svd",
    "model": "SVDDragunov",
    "name": "SVD",
    "allowed": [],
    "base": {
        "spread_mult": 1.6,
        "ammo_item_id": "ammo_pkm_762x54r",
        "ads_smooth": 11.5,
        "mag_size": 10,
        "recoil": 120,
        "camera_shake": 105,
        "fire_interval": 0.35,
        "reload_time": 3.6,
        "empty_reload_time": 4.6,
        "damage": 65,
        "bullet_speed": 520,
        "effective_range": 150,
        "stability_mult": 1.15,
    },
    "options": {},
}

FORMULA = {
    "source": "SVD_ITEM",
    "base": 15,
    "enhanceFlat": 1.05,
    "attrs": [
        {"key": "int", "base": 0.48, "perEnhance": 0.085},
        {"key": "wis", "base": 0.48, "perEnhance": 0.085},
    ],
}


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def save(name, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if CHECK:
        print('  [check] %s would be %d bytes (now %d)'
              % (name, len(text.encode('utf-8')), (DATA / name).stat().st_size))
        return
    (DATA / name).write_text(text, encoding='utf-8')
    print('  wrote %s (%d bytes)' % (name, len(text.encode('utf-8'))))


def insert_after_key(mapping, anchor, key, value):
    if key in mapping:
        mapping[key] = value
        return 'replaced'
    out = {}
    for k, v in mapping.items():
        out[k] = v
        if k == anchor:
            out[key] = value
    if key not in out:
        out[key] = value
        return 'appended (anchor %r missing)' % anchor
    mapping.clear()
    mapping.update(out)
    return 'inserted after %r' % anchor


print('items.json')
items = load('items.json')
print(' ', insert_after_key(items, 'ue_pkm_lowpoly', 'ue_svd', ITEM))
save('items.json', items)

print('gunsmith.json')
gunsmith = load('gunsmith.json')
weapons = gunsmith['weapons']
index = next((i for i, w in enumerate(weapons) if w['id'] == 'ue_pkm_lowpoly'), len(weapons) - 1)
existing = next((i for i, w in enumerate(weapons) if w['id'] == 'ue_svd'), None)
if existing is not None:
    weapons[existing] = WEAPON
    print('  replaced existing entry at %d' % existing)
else:
    weapons.insert(index + 1, WEAPON)
    print('  inserted after ue_pkm_lowpoly (index %d)' % index)
save('gunsmith.json', gunsmith)

print('combat-weapon-formulas.json')
formulas = load('combat-weapon-formulas.json')
print(' ', insert_after_key(formulas, 'ue_pkm_lowpoly', 'ue_svd', FORMULA))
save('combat-weapon-formulas.json', formulas)

if not CHECK:
    print('done')
