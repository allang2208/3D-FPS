"""Install this scoped bug fix; keep full garment visual acceptance pending.

This is not the new-garment gate and must not produce a fabricated visual pass.
Only replace the 15 firearm references explicitly captured for this repair.
"""
import json
from pathlib import Path
from garment_pipeline import read, write, digest, asset_file

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/ChainmailCameraClearance20260929'


def main():
    path = P / 'Content/ColdSteelData/modular_outfits.json'
    before_bytes = path.read_bytes()
    config = json.loads(before_bytes.decode('utf-8-sig'))
    current = config['items']['ue_chainmail_shirt']['rig_meshes']
    expected = read(R/'before.json')['sources']
    saved = read(R/'saved.json')
    if set(saved) != set(expected):
        raise RuntimeError('Not every firearm sleeve has been saved')
    for profile, source in expected.items():
        receipt = saved[profile]
        if current.get(profile) != source:
            raise RuntimeError('Active reference changed: ' + profile)
        if digest(asset_file(source)) != receipt['source_sha256']:
            raise RuntimeError('Source asset changed: ' + profile)
        if digest(asset_file(receipt['asset'])) != receipt['asset_sha256']:
            raise RuntimeError('Saved repair asset changed: ' + profile)
    write(R/'publication-before.json', config)
    for profile, receipt in saved.items():
        current[profile] = receipt['asset']
    encoded = (json.dumps(config, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    if path.read_bytes() != before_bytes:
        raise RuntimeError('Configuration changed before publication')
    path.write_bytes(encoded)
    write(R/'published.json', dict(profiles={p:v['asset'] for p,v in saved.items()},
        runtime_visual='pending', layer_clearance='pending',
        scope='User-authorized existing chainmail bug fix; not new garment acceptance',
        next_load='Next PIE/game session reads the saved configuration',
        config_sha256=digest(path)))
    print('CHAINMAIL_CAMERA_REPAIR_PUBLISHED', len(saved), 'profiles; runtime_visual=pending')


if __name__ == '__main__':
    main()
