"""Connect the saved view-only material set without replacing any rig mesh."""
import hashlib
import json
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/ChainmailCameraFade20260930'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    receipt = read(R / 'saved.json')
    build = read(R / 'native-build.json')
    if not build.get('complete'):
        raise RuntimeError('Camera-fade runtime integration has not been built')
    materials = []
    for row in receipt['materials']:
        path = P / 'Content' / (row['material'].split('.')[0].removeprefix('/Game/') + '.uasset')
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise RuntimeError('Saved camera-fade material changed: ' + str(path))
        materials.append(row['material'])
    path = P / 'Content/ColdSteelData/modular_outfits.json'
    raw = path.read_bytes()
    config = json.loads(raw.decode('utf-8-sig'))
    recipe = config['items']['ue_chainmail_shirt']
    if recipe['rig_meshes'] != receipt['source_rig_meshes'] or recipe.get('secondary_motion') != 'chainmail_shared_sway_v1':
        raise RuntimeError('Active chainmail recipe changed during authoring; preserve its current state')
    backup = R / 'configuration-before.json'
    if not backup.exists():
        backup.write_bytes(raw)
    recipe['first_person_materials'] = materials
    if path.read_bytes() != raw:
        raise RuntimeError('Concurrent outfit configuration edit; no write performed')
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (R / 'published.json').write_text(json.dumps({'first_person_materials': materials,
        'rig_meshes_preserved': recipe['rig_meshes'], 'runtime_tested': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('CHAINMAIL_CAMERA_FADE_PUBLISHED', len(materials), 'materials; meshes unchanged')


if __name__ == '__main__':
    main()
