"""Publish only the destruction rune's visual recipe and copy into its authoring base."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
M = '/Game/Weapons/RuneboundWarhammer20261022/DestructionRedImpactV2/M_RuneboundDestructionRuneSurface.M_RuneboundDestructionRuneSurface'
ID = 'destruction_mana_rune'
DESCRIPTION = '符文战锤专属。赤红魔力沿原生刻纹汇聚，苏醒时裂光迸发，命中后魔力碎片炸开飘散。'
APPEARANCE = '原生刻纹强化 · 赤红聚能 · 爆裂余烬'
EFFECT = '聚能崩解｜赤红魔力沿原生刻纹涌动；苏醒命中时从锤头炸开光屑与碎片，减速飘散并上浮消失。'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def publish():
    imported = read(P/'import_receipt.json')
    built = read(P/'build_receipt.json')
    if not imported.get('complete') or len(imported.get('assets', [])) != 2:
        raise RuntimeError('Save the two new materials before publishing')
    for asset in imported['assets']:
        package = ROOT/'Content'/(asset.removeprefix('/Game/').split('.')[0]+'.uasset')
        if not package.is_file():
            raise RuntimeError('Install saved output before publishing '+str(package))
    ready = {r['target'] for r in built['targets'] if r['exit_code'] == 0}
    if 'FPSGAMEEditor' not in ready:
        raise RuntimeError('Complete the Editor native build before publishing')
    game_ready = 'FPSGAME' in ready
    files = {
        ROOT/'Content/ColdSteelData/runebound-warhammer-modules.json': 'catalog',
        ROOT/'Content/ColdSteelData/runebound-warhammer-gunsmith.json': 'bench',
        P.parent/'ModulesV1/catalog_base.json': 'catalog',
        P.parent/'ModulesV1/workbench.json': 'bench',
    }
    published = []
    for path, kind in files.items():
        before = path.read_bytes()
        value = json.loads(before.decode('utf-8-sig'))
        if kind == 'catalog':
            rune = value['slots']['rune'][ID]
            rune['appearance'] = APPEARANCE
            rune['surface_materials'] = {key: M for key in rune['surface_materials']}
        else:
            rune = next(o for c in value['columns'] if c['key'] == 'rune'
                        for o in c['options'] if o.get('id') == ID)
            rune['description'], rune['appearance'] = DESCRIPTION, APPEARANCE
            rune['special_effects'] = [EFFECT if line.startswith('聚能崩解｜') else line for line in rune['special_effects']]
        backup = P/'Before'/path.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(before)
        if path.read_bytes() != before:
            raise RuntimeError('Concurrent write to '+str(path))
        temp = path.with_name(path.name+'.runebound-red-v2.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        os.replace(temp, path)
        published.append(str(path.relative_to(ROOT)))
    receipt = {
        'complete': game_ready, 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'published_data': True, 'editor_native_ready': True, 'standalone_game_ready': game_ready,
        'weapon': 'ue_runebound_warhammer', 'rune': ID, 'files': published, 'assets': imported['assets'],
        'native_builds': built['targets'], 'geometry_capacity': 1020, 'burst_slots': 4,
        'destruction_ambient_motes': 60, 'destruction_motes_per_hit': 240,
        'colours': {'factory': 'blue', 'swift': 'blue', 'destruction': 'red'},
        'burst_space': 'world space from the displayed hammer head at impact',
        'gameplay_balance_modified': False, 'animations_modified': False,
        'tests_run': False, 'game_started': False, 'editor_ui_started': False,
        'build_unblock_changes': 'FacilityEncounterPacing.cpp: add Character.h and rename local Role variables only',
        'remaining': [] if game_ready else ['Standalone Game build blocked by incomplete AHeQueMonster pump-control interfaces; see build log'],
    }
    (P/'delivery_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('RUNEBOUND_RED_IMPACT_PUBLISHED')

if __name__ == '__main__':
    publish()
