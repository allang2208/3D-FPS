"""Scoped data merge for the approved Pan Chi effect. Does not initialize saves."""
import json
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
EFFECT = json.loads((P / 'effects.json').read_text(encoding='utf-8'))

def update(path, edit):
    before = path.read_bytes()
    data = json.loads(before.decode('utf-8-sig'))
    edit(data)
    if path.read_bytes() != before:
        raise RuntimeError('Concurrent edit preserved: ' + str(path))
    tmp = path.with_suffix(path.suffix + '.panchi-effects.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)

def install():
    def option(data):
        guard = next(c for c in data['columns'] if c['key'] == 'guard')
        row = next(o for o in guard['options'] if o['id'] == 'panchi_zhanyue')
        row.update(EFFECT)
    update(ROOT / 'Content/ColdSteelData/melee-gunsmith.json', option)
    def status(data):
        rows = [
            {'type': 'panchiCharge', 'name': '蟠螭蓄势', 'icon': '螭', 'color': '#e7be70',
             'description': '至少1层蓄势且冷却就绪时，主动上挑免准备释放强化升龙。金龙造成完整重击100%的魔法伤害，本次上挑每层额外削韧+20%（最多3层）；释放时无需命中，将阵心半径10米内的普通或已破韧怪物向阵心拉近最多5米。', 'kind': 'buff', 'group': 'triggered'},
            {'type': 'panchiCooldown', 'name': '双螭调息', 'icon': '岳', 'color': '#bd9256',
             'description': '强化升龙正在冷却，仍可通过格挡蓄势。冷却就绪后由下一次主动上挑触发免准备的升龙金阵。切换武器不重置冷却。', 'kind': 'cooldown', 'group': 'triggered'}]
        for row in rows:
            existing = next((o for o in data['effects'] if o['type'] == row['type']), None)
            if existing is None: data['effects'].append(row)
            else: existing.update(row)
    update(ROOT / 'Content/ColdSteelData/status_effects.json', status)
    update(P.parent / 'PanChiGuard20261006/guard_manifest.json', lambda d: d.update(stats=EFFECT['stats'],
        effect_revision='PanChiFormationPull20261007', effect_name='强化升龙',
        effect_art='../PanChiUppercut20261007/GuardSeal/PanChi_GuardSeal_V1.png'))
    (P / 'catalog_receipt.json').write_text(json.dumps({'complete': True, 'id': 'panchi_zhanyue',
        'tier': 'special', 'stats': EFFECT['stats'], 'runtime_tested': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PANCHI_EFFECT_CATALOG_SAVED')

if __name__ == '__main__': install()
