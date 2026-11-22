"""Publish village seat/mattress anchors and restore the saved native chapel takes."""
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAPEL = ROOT/'SourceAssets/ChapelFurniture20261116'
DATA = ROOT/'Content/ColdSteelData'
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))


def publish():
    pew = read(CHAPEL/'publication.json')['profile']
    saved = read(CHAPEL/'HangingHandsR3/assets_saved.json')
    body_path = DATA/'player_body.json'
    before = body_path.read_bytes()
    body = json.loads(before.decode('utf-8-sig'))
    owned = []
    for variant, roles in saved['variants'].items():
        node = body if variant=='default' else body['body_variants'][variant]
        parent = () if variant=='default' else ('body_variants',variant)
        for role,path in roles.items():
            if not (ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).is_file():
                raise FileNotFoundError(path)
            node['clips'][role] = path
            node.setdefault('furniture_camera_tracks',{})[role] = saved['camera_tracks'][variant][role]
            owned.extend([parent+('clips',role),parent+('furniture_camera_tracks',role)])
    transaction = runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
    body_receipt = transaction(body_path,before,body,owned_paths=owned,producer=__file__)
    timing = {key: {'duration': track['duration'], 'camera': [p+[0,0] for p in track['eyes']]}
              for key,track in saved['camera_tracks']['default'].items()}
    village = read(Path(__file__).with_name('village_slots.json'))
    pew_type = dict(lying=False,surface_height=pew['slots'][0]['seat'][2]*pew['scale'][2],
                    entry_offset=[0,70,0],entry_yaw=0)
    result = dict(types={'ChapelPew':pew_type},furniture=[*village,pew],clips=timing)
    path = DATA/'village_furniture_rest.json'
    path.with_suffix('.village.tmp').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path.with_suffix('.village.tmp').replace(path)
    return body_receipt


if __name__=='__main__':
    print(json.dumps(publish(),ensure_ascii=True))
