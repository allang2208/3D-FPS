"""Retain the installed RSH option and stats; update its approved exterior description."""
import json
import re
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]
OPTION = 'rsh12_heavy_suppressor'
DESCRIPTION = 'RSH-12 专属加长方盒消音器，削角外壳带连续侧槽，阶梯接座贴合枪口护罩，抑制枪声和枪口火光。'

def apply_weapon(weapon):
    option = next((o for o in weapon['options']['muzzle'] if o['id'] == OPTION), None)
    if option is None:
        prior = json.loads((O.parent / 'RSH12HeavySuppressor20261004/catalog_receipt.json').read_text(encoding='utf8'))
        option = prior['option']
        weapon['options']['muzzle'].append(option)
    option['description'] = DESCRIPTION
    return option

if __name__ == '__main__':
    model = json.loads((O / 'import_receipt.json').read_text(encoding='utf8'))
    icon = json.loads((O / 'icon_receipt.json').read_text(encoding='utf8'))
    if not model.get('complete'):
        raise RuntimeError('Cube model has not finished saving')
    path = P / 'Content/ColdSteelData/gunsmith.json'
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    decoder = json.JSONDecoder()
    pos = text.index('[', text.index('"weapons"')) + 1
    while True:
        while text[pos].isspace() or text[pos] == ',':
            pos += 1
        weapon, end = decoder.raw_decode(text, pos)
        if weapon['id'] == 'ue_rsh12':
            break
        pos = end
    option = apply_weapon(weapon)
    indent = re.search(r'[^\S\n]*$', text[:pos]).group()
    replacement = json.dumps(weapon, ensure_ascii=False, indent=2).replace('\n', '\n' + indent)
    backup = O / 'Before/gunsmith.json'
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():
        backup.write_bytes(raw)
    if path.read_bytes() != raw:
        raise RuntimeError('Catalog changed while preparing RSH cube entry')
    path.write_bytes((text[:pos] + replacement + text[end:]).encode('utf8'))
    (O / 'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',
        option=option, mesh=model['mesh'], icon=icon['texture'],
        save_id_changed=False, stats_changed=False, runtime_tested=False), ensure_ascii=False, indent=2), encoding='utf8')
    print('RSH_CUBE_CATALOG_SAVED')
