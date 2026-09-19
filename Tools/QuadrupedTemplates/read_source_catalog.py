"""Read the installed pack's source metadata; no playback, renders or asset saves."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / 'SourceAssets/QuadrupedTemplates'
PACK = PROJECT / 'Content/AnimalVarietyPack'
OUT.mkdir(parents=True, exist_ok=True)

def asset_path(file):
    return '/Game/' + file.relative_to(PROJECT / 'Content').with_suffix('').as_posix()

catalog = {
    'source': 'https://www.fab.com/listings/2dd7964c-a601-4264-a53d-465dcae1644c',
    'publisher': 'PROTOFACTOR INC',
    'scope': 'Installed asset metadata only; animation appearance and contact frames not reviewed.',
    'animations': [], 'meshes': [],
}
for file in sorted(PACK.glob('*/Animations/*.uasset')):
    asset = u.load_asset(asset_path(file))
    if not isinstance(asset, u.AnimSequence):
        continue
    intervals = u.AnimationLibrary.get_num_frames(asset)
    seconds = asset.get_play_length()
    names = u.AnimationLibrary.get_animation_notify_event_names(asset)
    catalog['animations'].append({
        'name': asset.get_name(), 'asset': asset.get_path_name(),
        'skeleton': asset.get_editor_property('skeleton').get_path_name(),
        'seconds': seconds, 'frame_intervals': intervals,
        'keys_including_t0': intervals + 1,
        'sample_rate_from_intervals_per_second': intervals / seconds if seconds else None,
        'enable_root_motion': asset.get_editor_property('enable_root_motion'),
        'force_root_lock': asset.get_editor_property('force_root_lock'),
        'rate_scale': asset.get_editor_property('rate_scale'),
        'notify_names': [str(name) for name in names],
        'contact_seconds': None,
    })
for file in sorted(PACK.glob('*/Meshes/SK_*.uasset')):
    if file.stem.endswith(('_Skeleton', '_PhysicsAsset')):
        continue
    mesh = u.load_asset(asset_path(file))
    if not isinstance(mesh, u.SkeletalMesh):
        continue
    comp = u.SkeletalMeshComponent()
    comp.set_skeletal_mesh_asset(mesh)
    bones = [comp.get_bone_name(index) for index in range(comp.get_num_bones())]
    catalog['meshes'].append({
        'name': mesh.get_name(), 'asset': mesh.get_path_name(),
        'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
        'physics_asset': mesh.get_editor_property('physics_asset').get_path_name() if mesh.get_editor_property('physics_asset') else None,
        'bones': [{'name': str(b), 'parent': str(comp.get_parent_bone(b))} for b in bones],
    })
(OUT / 'source_catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('QUADRUPED_SOURCE_CATALOG_WRITTEN')
