"""Save Tang Dao-only whirlwind variants, retaining every source bone track."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonTangDaoWhirlwind20261010'
spec_path = OUT / 'edge-roll.json'
spec = json.loads(spec_path.read_text())
digest = hashlib.sha256(spec_path.read_bytes()).hexdigest()
lib = u.EditorAssetLibrary
if u.EditorLevelLibrary.get_pie_worlds(True):
    raise RuntimeError('Exit PIE before saving Tang Dao whirlwind variants.')
receipt = {'complete': False, 'source_hash': digest, 'clips': {}}
for phase, take in spec['clips'].items():
    path = take['destination']
    clip = u.load_asset(path) if lib.does_asset_exist(path) else None
    if clip and lib.get_metadata_tag(clip, 'TangDaoEdgeSourceHash') != digest:
        raise RuntimeError('This asset belongs to another authoring revision: ' + path)
    if not clip:
        clip = lib.duplicate_asset(take['source_asset'], path)
        if not clip:
            raise RuntimeError('Cannot duplicate ' + take['source_asset'])
        u.AnimationLibrary.remove_curve(clip, 'SwordGripRoll', False)
        u.AnimationLibrary.add_curve(clip, 'SwordGripRoll')
        u.AnimationLibrary.add_float_curve_keys(clip, 'SwordGripRoll', take['times'], take['SwordGripRoll'])
        lib.set_metadata_tag(clip, 'TangDaoEdgeSourceHash', digest)
        lib.set_metadata_tag(clip, 'TangDaoEdgeSource', take['source_asset'])
        lib.set_metadata_tag(clip, 'AuthoringScript', 'SourceAssets/ThirdPersonTangDaoWhirlwind20261010/author_edge_roll.py')
        lib.set_metadata_tag(clip, 'GripRevision', '20261010-tang-dao-whirlwind-edge')
        lib.set_metadata_tag(clip, 'GripCurve', 'SwordGripRoll: 0 to -180 in windup, -180 during spin, return to 0 in recovery')
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Cannot finalize ' + path)
    if not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Cannot save ' + path)
    receipt['clips'][take['config_key']] = clip.get_path_name()
    (OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('TANG_DAO_WHIRLWIND_SAVED ' + clip.get_path_name())
receipt['complete'] = True
(OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('TANG_DAO_WHIRLWIND_SAVE_COMPLETE')
