"""Publish compact, hash-linked evidence from completed local runtime runs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

root = Path('D:/FPS3D/FPSGAME')
suites = {
    'poison_maggot_arena': ('Saved/PoisonMaggot/arena-final/acceptance.json', 'Saved/PoisonMaggot/arena-final/play.log'),
    'poison_maggot_village': ('Saved/PoisonMaggot/village-final/acceptance.json', 'Saved/PoisonMaggot/village-final/village-play.log'),
    'shared_monster_ai': ('Saved/MonsterAI/acceptance.json', 'Saved/MonsterAI/play.log'),
    'nurse_regression': ('Saved/NurseZombie/validation-result.json', 'Saved/MonsterAI/nurse-regression.log'),
    'handbrain_regression': ('Saved/HandBrain/acceptance.json', 'Saved/PoisonMaggot/handbrain-regression.log'),
}

def evidence(path):
    p = root / path
    return {'path': path, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'modified_utc': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()}

report = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
          'engine': 'UE 5.8.2, standalone game process, D3D12',
          'scope': 'Tool-driven runtime and rendered visual inspection; no packaged or multiplayer acceptance',
          'suites': {}}
for name, (data_path, log_path) in suites.items():
    data = json.loads((root / data_path).read_text(encoding='utf-8-sig'))
    assert data.get('passed') and not data.get('failed') and data.get('complete', True), name
    report['suites'][name] = {'passed_count': len(data['passed']), 'failed_count': 0,
                             'checks': data['passed'], 'report': evidence(data_path), 'log': evidence(log_path)}
report['exports'] = json.loads((root / 'SourceAssets/PoisonMaggot20260911/previews/export_validation.json').read_text())
arena_log = (root / suites['poison_maggot_arena'][1]).read_text(encoding='utf-8-sig')
village_log = (root / suites['poison_maggot_village'][1]).read_text(encoding='utf-8-sig')
arena_min = float(re.search(r'MAGGOT_CORPSE.*?Min=\(.*?Z=([-\d.]+)\)', arena_log)[1])
village_gap = float(re.search(r'MAGGOT_VILLAGE_CORPSE gap=([-\d.]+)', village_log)[1])
report['measurements_cm'] = {'arena_max_side': json.loads((root / suites['poison_maggot_arena'][0]).read_text(encoding='utf-8-sig'))['max_side_cm'],
                             'arena_actual_surface_min_z': arena_min, 'village_actual_surface_min_ground_gap': village_gap,
                             'allowed_ground_penetration': 3.0}
report['visual_evidence'] = [evidence(p) for p in [
    'SourceAssets/PoisonMaggot20260911/previews/PoisonMaggot_Actions.gif',
    'Saved/PoisonMaggot/arena-final/spit-release.png',
    'Saved/PoisonMaggot/arena-final/corpse.png',
    'Saved/PoisonMaggot/arena-final/weapon-hit.png',
    'Saved/PoisonMaggot/village-final/village-spit.png',
    'Saved/PoisonMaggot/village-final/village-corpse.png']]
(root / 'Docs/PoisonMaggotAcceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MAGGOT_ACCEPTANCE_RECORDED', {name: data['passed_count'] for name, data in report['suites'].items()})
