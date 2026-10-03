"""Translate original surface attachment records into the new rig input."""
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV06')
regions = json.loads((ROOT/'regions/region_authoring_original_v06.json').read_text(encoding='utf-8'))
guides = {}
for panel in regions['membrane_tip_guides']:
    identifier = int(panel['id'])
    y = panel['root_source'][1]
    side = 'l' if identifier <= 3 else 'r'
    parent = 'head' if y > .64 else 'neck_02' if y > .56 else 'clavicle_'+side
    guides[str(identifier)] = {
        'root_source': panel['root_source'], 'tip_source': panel['tip_source'],
        'root_source_vertex_id': panel['root_source_vertex_id'],
        'tip_source_vertex_id': panel['tip_source_vertex_id'], 'parent_bone': parent,
        'source_region': identifier, 'method': 'Actual original leaf and body attachment source vertex IDs',
    }
(ROOT/'gill_reference_guides_source.json').write_text(json.dumps(guides, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_ORIGINAL_GILL_REFERENCE_INPUT_AUTHORED', flush=True)
