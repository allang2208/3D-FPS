"""Record completed production files; no model tests or render steps."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / 'Meshy/candidate01'
response = json.loads((TASK / 'response.json').read_text(encoding='utf-8'))
manifest = json.loads((TASK / 'downloads.json').read_text(encoding='utf-8'))
delivery = {
    'asset': 'A762',
    'version': 'Meshy_Candidate01',
    'task_id': response['id'],
    'generation_status': response['status'],
    'consumed_credits': response.get('consumed_credits'),
    'parameters': json.loads((ROOT / 'meshy_settings.json').read_text(encoding='utf-8'))['common'],
    'outputs': [entry['file'] for entry in manifest],
    'editable_source': 'A762_Meshy_Candidate01_Editable.blend',
    'scale': 'Generator original scale, not a measured dimensional replica',
    'source_images': ['References/user_01_color_side.png', 'References/user_02_clay_threequarter.png'],
    'generated_reference_views': ['References/a762_side.png', 'References/a762_front_threequarter.png', 'References/a762_rear_threequarter.png'],
    'mesh_processing': 'Original cloud geometry and materials preserved in editable Blender project',
    'user_selected': False,
    'mechanical_parts_split': False,
    'rigged': False,
    'imported_into_ue': False,
    'gameplay_integrated': False,
    'tested': False,
    'visual_acceptance': 'For user evaluation; no local render or acceptance inspection performed',
}
(ROOT / 'DELIVERY.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'delivery_record': str(ROOT / 'DELIVERY.json'), 'generation': response['status'], 'credits': response.get('consumed_credits'), 'output_count': len(manifest)}, ensure_ascii=False))
