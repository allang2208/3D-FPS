"""Publish the user's RSH-only spread and square-sight revision, without compounding."""
import copy
import json
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]
# The installed base omitted spread_mult, so GunsmithSystem used 1.0.
PREVIOUS_BASE_SPREAD = 1.0
BASE_SPREAD = PREVIOUS_BASE_SPREAD * 4.0
SQUARE = 'rsh12_square_sight'
TACTICAL_SQUARE = 'rsh12_tactical_square_sight'

def apply_weapon(weapon):
    if weapon.get('id') != 'ue_rsh12':
        return
    weapon['base']['spread_mult'] = BASE_SPREAD
    options = []
    seen = set()
    for option in weapon['options']['optic']:
        option['id'] = {'holographic': SQUARE, 'eoth_holographic': TACTICAL_SQUARE}.get(option['id'], option['id'])
        if option['id'] == SQUARE:
            option['name'] = '方形瞄准镜'
            option['description'] = 'RSH-12 专属方形瞄具，开放式短镜框与低位夹座贴合上导轨，保留环点分划。'
            option['effects'] = [dict(text='1倍瞄准', benefit=0), dict(text='开镜耗时降低5%', benefit=1)]
            option.setdefault('stats', {})['ads_percent'] = -0.05
        elif option['id'] == TACTICAL_SQUARE:
            option['name'] = '战术方形瞄准镜'
            option['description'] = 'RSH-12 专属战术方形瞄具，短保护罩、独立透光镜片与环点分划，提供固定低倍瞄准。'
            option['effects'] = [dict(text='固定1.5倍瞄准', benefit=0),
                                 dict(text='开镜耗时降低5%', benefit=1)]
            option.setdefault('stats', {})['ads_percent'] = -0.05
        if option['id'] not in seen:
            options.append(option)
            seen.add(option['id'])
    weapon['options']['optic'] = options

if __name__ == '__main__':
    path = P / 'Content/ColdSteelData/gunsmith.json'
    raw = path.read_bytes()
    text = raw.decode('utf-8')
    decoder = json.JSONDecoder()
    pos = text.index('[', text.index('"weapons"')) + 1
    while True:
        while text[pos].isspace() or text[pos] == ',':
            pos += 1
        weapon, end = decoder.raw_decode(text, pos)
        if weapon['id'] == 'ue_rsh12':
            break
        pos = end
    previous = copy.deepcopy(weapon)
    apply_weapon(weapon)
    backup = O / 'Before/gunsmith.json'
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():
        backup.write_bytes(raw)
    line_prefix = text[:pos].rsplit('\n', 1)[-1]
    indent = ''.join(c for c in line_prefix if c in ' \t')
    replacement = json.dumps(weapon, ensure_ascii=False, indent=2).replace('\n', '\n' + indent)
    if path.read_bytes() != raw:
        raise RuntimeError('Catalog changed during RSH square-sight publication')
    path.write_bytes((text[:pos] + replacement + text[end:]).encode('utf8'))
    optics = [v for v in weapon['options']['optic'] if v['id'] in (SQUARE, TACTICAL_SQUARE)]
    (O / 'catalog_receipt.json').write_text(json.dumps(dict(
        weapon='ue_rsh12', previous_base_spread=previous['base'].get('spread_mult', 1.),
        target_base_spread=BASE_SPREAD, requested_multiplier=4, options=optics,
        optic_models_changed=False, option_ids_changed=True, rsh_exclusive=True, runtime_tested=False,
    ), ensure_ascii=False, indent=2), encoding='utf8', newline='\n')
    print('RSH_SQUARE_OPTICS_AND_BASE_SPREAD_PUBLISHED')
