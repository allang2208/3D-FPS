"""Author Kaitlin's material partitions without changing her native surface."""
import json
from pathlib import Path
import numpy as np

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
INPUT = WORK / 'FitInputs'
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
body, modular, captured = [read(INPUT / (name + '.json')) for name in ('player_body', 'modular_outfits', 'captured')]
profile = modular['profiles'][body['body_mesh']]
source = read(INPUT / captured[profile['native_bare_skin']]['file'])
target = read(WORK / 'NativeGeometry/MHC_Kaitlin_Body.json')
correspondence = read(WORK / 'body_correspondence.json')
slots = np.asarray(source['triangle_materials'], int)[correspondence['target_to_source_triangles']]
skin_material = target['materials'][0]['asset']
materials = [{'slot': item['slot'], 'asset': skin_material} for item in source['materials']]
output = WORK / 'Body'
output.mkdir(exist_ok=True)
asset = '/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/Body/SK_Kaitlin_Base'
(output / 'segmented_body.json').write_text(json.dumps({
    'source': target['source'], 'asset': asset, 'materials': materials,
    'triangle_materials': slots.tolist(), 'geometry': 'unchanged_complete_native_body',
    'coverage_source': profile['native_bare_skin'], 'profile': profile,
    'authoring_method': correspondence['method']}, separators=(',', ':')), encoding='utf-8')
print('KAITLIN_BODY_PARTITIONS_AUTHORED', len(slots), len(materials), flush=True)
