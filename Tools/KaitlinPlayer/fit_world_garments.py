"""Create female world-garment authoring positions from the captured native bodies."""
import hashlib
import json
from pathlib import Path
from body_surface_fit import BodySurfaceFit

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
INPUT = WORK / 'FitInputs'
OUTPUT = WORK / 'WorldGarments'
OUTPUT.mkdir(exist_ok=True)
inventory = json.loads((INPUT / 'inventory.json').read_text(encoding='utf-8'))
captured = json.loads((INPUT / 'captured.json').read_text(encoding='utf-8'))
body = json.loads((INPUT / 'player_body.json').read_text(encoding='utf-8-sig'))
modular = json.loads((INPUT / 'modular_outfits.json').read_text(encoding='utf-8-sig'))
skin_path = modular['profiles'][body['body_mesh']]['native_bare_skin']
source_skin = json.loads((INPUT / captured[skin_path]['file']).read_text(encoding='utf-8'))
target_skin = json.loads((WORK / 'NativeGeometry/MHC_Kaitlin_Body.json').read_text(encoding='utf-8'))
correspondence = json.loads((WORK / 'body_correspondence.json').read_text(encoding='utf-8'))
fit = BodySurfaceFit(source_skin, target_skin, correspondence['target_to_source_vertices'])
manifest = {}
for row in inventory['meshes']:
    if 'garment' not in row['roles']:
        continue
    if not any(any(part == 'Jason' or isinstance(part, str) and '/SK_Jason_' in part for part in selector)
               for selector in row['selectors']):
        continue
    path = row['source']
    source = json.loads((INPUT / captured[path]['file']).read_text(encoding='utf-8'))
    result = fit.garment(source)
    # MetaHuman body UV identities were captured from both native surfaces.
    # Exposed skin patches embedded in garment meshes retain those UVs and
    # must use Kaitlin's skin, including the paired owner-view patches.
    for material in result['materials']:
        if ('Skin' in material['slot'] and material['slot'] != 'MaskedProxy'
                or material['slot'] == 'DefaultSleeves'):
            material['asset'] = target_skin['materials'][0]['asset']
    digest = hashlib.sha256(path.encode()).hexdigest()[:8]
    name = 'SK_Kaitlin_' + path.rsplit('.', 1)[-1].removeprefix('SK_Jason_') + '_' + digest
    file = OUTPUT / (digest + '.json')
    result['source_sha256'] = source['source_sha256']
    file.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
    manifest[path] = {'geometry': str(file), 'asset': '/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/World/' + name,
                       'source_sha256': source['source_sha256'], 'selectors': row['selectors']}
    print('KAITLIN_WORLD_GARMENT_AUTHORED', name, flush=True)
(OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('KAITLIN_WORLD_GARMENTS_AUTHORED', len(manifest))
