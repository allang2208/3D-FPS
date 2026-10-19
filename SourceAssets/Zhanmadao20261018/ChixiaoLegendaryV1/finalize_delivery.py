import json
import sys
from datetime import datetime
from pathlib import Path

P = Path(__file__).resolve().parent
attempt = sys.argv[1] if len(sys.argv) > 1 else 'legendary-01'
read = lambda file: json.loads((P / file).read_text('utf-8-sig'))
publication = read('publication.json')
builds = [read(f'build-{target}-receipt-{attempt}.json') for target in ('FPSGAMEEditor', 'FPSGAME')]
if not publication['published'] or any(build['exit_code'] for build in builds):
    raise RuntimeError('Asset publication or native build unfinished')
receipt = dict(publication, name='赤霄', weapon='ue_zhanmadao', slot='blade_1', option='chixiao',
    completed_at=datetime.now().astimezone().isoformat(), native_builds=builds,
    heavy_trail='crimson_blade_path', beiwei_combination='red_heavy_gold_other_martial',
    perspective_support=['first_person', 'third_person', 'network_observer'],
    visual_acceptance=False, runtime_tested=False)
(P / 'delivery.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('CHIXIAO_LEGENDARY_DELIVERED', flush=True)
