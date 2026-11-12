"""Freeze the current female ST6 routes and native neck production inputs."""
import hashlib
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/ST6FemaleCollar20261108'
DEST = '/Game/Characters/ModularOutfit20260924/ST6FemaleCollar20261108'


def main():
    (WORK / 'Inputs').mkdir(parents=True, exist_ok=True)
    config_bytes = (PROJECT / 'Content/ColdSteelData/modular_outfits.json').read_bytes()
    config = json.loads(config_bytes.decode('utf-8-sig'))
    item = config['body_variants']['kaitlin']['items']['ue_st6_sleeves']
    routes = {}

    def walk(value, selector):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, selector + [key])
        elif isinstance(value, str) and '/KaitlinPlayer20261023/World/' in value:
            routes.setdefault(value, []).append(selector)

    walk(item, ['body_variants', 'kaitlin', 'items', 'ue_st6_sleeves'])
    meshes = []
    for source, selectors in routes.items():
        name = source.rsplit('.', 1)[-1]
        digest = hashlib.sha256(source.encode()).hexdigest()[:12]
        meshes.append(dict(source=source, selectors=selectors, file=digest + '.json',
                           asset=DEST + '/' + name + '_NeckFit'))
    player = json.loads((PROJECT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    female = player['body_variants']['kaitlin']
    natives = [dict(source=female['heads'][female['default_head']]['mesh'], file='head.json'),
               dict(source=female['body_mesh'], file='body.json')]
    (WORK / 'Inputs/modular_outfits.json').write_bytes(config_bytes)
    (WORK / 'manifest.json').write_text(json.dumps(dict(meshes=meshes, natives=natives,
        item='ue_st6_sleeves', variant='kaitlin', destination=DEST), indent=2), encoding='utf-8')
    print('ST6_FEMALE_INPUTS', len(meshes), 'meshes;', sum(map(len, routes.values())), 'routes')


if __name__ == '__main__':
    main()
