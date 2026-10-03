"""Read only the live AKM/A762 standard and extended-magazine dependencies."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
jobs = []
for gun in ('AKM', 'A762'):
    for family in ('base', 'angled', 'vertical', 'prism', 'canted'):
        for clip in ('reload', 'reload_empty'):
            suffix = ('' if family == 'base' else family + '_') + clip
            if gun == 'AKM':
                folder = {'base':'ReloadPolish', 'angled':'GripErgonomic',
                          'vertical':'GripVRENatural', 'prism':'GripVREExtensions',
                          'canted':'GripVREExtensions'}[family]
                path = f'/Game/Weapons/AKMIntegration/SovietFab/{folder}/{family}/A_AKM_{suffix}'
            elif family == 'base':
                path = f'/Game/Weapons/A762/Integrated20260920/Animations/A_A762_{clip}'
            else:
                path = f'/Game/Weapons/A762/Accessories05/Animations/{family}/A_A762_{family}_{clip}'
            jobs.append(dict(gun=gun, family=family, clip=clip, magazine='standard', asset=path))
            if gun == 'AKM':
                jobs.append(dict(gun=gun, family=family, clip=clip, magazine='extended',
                                 asset=f'/Game/Weapons/ExtMagContact20260919/A_AKM_ExtContact_{suffix}'))
for job in jobs:
    a = u.load_asset(job['asset'])
    if not a:
        raise RuntimeError(job['asset'])
    job.update(source=list(a.get_editor_property('asset_import_data').extract_filenames()),
               seconds=a.get_play_length(), skeleton=a.get_editor_property('skeleton').get_path_name(),
               compression=a.get_editor_property('bone_compression_settings').get_path_name())
meshes = {}
for key, path in {
    'AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
    'A762':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
    'A762_extended':'/Game/Weapons/A762/Accessories05/Meshes/SM_A762_ext_mag',
}.items():
    a = u.load_asset(path)
    if not a:
        raise RuntimeError(path)
    meshes[key] = dict(asset=path, source=list(a.get_editor_property('asset_import_data').extract_filenames()))
(OUT/'sources.json').write_text(json.dumps(dict(animations=jobs, meshes=meshes), indent=2), encoding='utf-8')
print('READ_MAGAZINE_GRIP_SOURCES', len(jobs), meshes)
