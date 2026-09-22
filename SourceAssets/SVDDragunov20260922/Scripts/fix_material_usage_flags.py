"""Fix the SVD materials' usage flags by copying them from the running M4 weapon material.

The play session log shows why the weapon reads as a checkerboard:

    LogMaterial: Warning: Material .../MI_SVD_Body missing usage flag SkeletalMesh!
                 Default Material will be used in game.
    LogSkeletalMesh: Warning: Material with missing usage flag was applied to skeletal mesh
                     /Game/Weapons/SVDDragunov20260922/Viewmodel/SK_SVD_Manny

Materials created from Python never got the "Used with Skeletal Mesh" flag, so UE refuses
every permutation and substitutes the default material. The flags are copied from the M4's
accepted weapon material rather than guessed, then each material is recompiled and saved.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
BASE = SPEC['content_root']
LIB = u.MaterialEditingLibrary
E = u.EditorAssetLibrary

# the M4's live weapon material: the reference for which usage flags a viewmodel needs
REFERENCE = '/Game/Weapons/M4InfimaV3/MI_Manny_01'

# UE property names for the material usage flags
FLAGS = ['used_with_skeletal_mesh', 'used_with_static_meshes', 'used_with_instanced_static_meshes',
         'used_with_particle_sprites', 'used_with_niagara_sprites', 'used_with_niagara_ribbons',
         'used_with_niagara_mesh_particles', 'used_with_morph_targets', 'used_with_spline_meshes',
         'used_with_geometry_collections', 'used_with_clothing', 'used_with_water',
         'used_with_hair_strands', 'used_with_lidar_point_cloud', 'used_with_volumetric_cloud',
         'used_with_ui', 'used_with_beam_trails', 'used_with_rect_lights', 'used_with_light_functions',
         'used_with_virtual_heightfield_mesh', 'used_with_gpu_scene']

reference = u.load_asset(REFERENCE)
if not isinstance(reference, u.MaterialInterface):
    raise RuntimeError('reference material not found: %s' % REFERENCE)
parent = reference
if isinstance(reference, u.MaterialInstance):
    parent = reference.get_editor_property('parent')
if not isinstance(parent, u.Material):
    raise RuntimeError('reference has no base material')

reference_flags = {}
for flag in FLAGS:
    try:
        reference_flags[flag] = bool(parent.get_editor_property(flag))
    except Exception:  # noqa: BLE001
        pass
print('REFERENCE_FLAGS ' + json.dumps({k: v for k, v in reference_flags.items() if v}))

report = {'reference_flags_on': [k for k, v in reference_flags.items() if v], 'materials': {}}
for part in SPEC['parts']:
    name = 'M_SVD_%s' % part['part_name']
    material = u.load_asset('%s/Materials/%s' % (BASE, name))
    if not isinstance(material, u.Material):
        report['materials'][name] = {'found': False}
        continue
    before = {}
    changed = []
    for flag in FLAGS:
        if flag not in reference_flags:
            continue
        try:
            before[flag] = bool(material.get_editor_property(flag))
        except Exception:  # noqa: BLE001
            continue
        if reference_flags[flag] and not before[flag]:
            material.set_editor_property(flag, True)
            changed.append(flag)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('%s compile errors: %s' % (name, errors))
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('%s save failed' % name)
    after = {flag: bool(material.get_editor_property(flag)) for flag in before}
    report['materials'][name] = {'changed': changed, 'before': before, 'after': after}
    print('MATERIAL_FLAGS %s changed=%s' % (name, changed))

# verify every instance now reports the flag through its parent
verify = {}
for part in SPEC['parts']:
    mi = u.load_asset('%s/Materials/MI_SVD_%s' % (BASE, part['part_name']))
    if isinstance(mi, u.MaterialInstanceConstant):
        base = mi.get_editor_property('parent')
        verify[part['part_name']] = bool(base.get_editor_property('used_with_skeletal_mesh')) if base else None
report['instances_report_skeletal_mesh'] = verify
report['all_ok'] = all(v is True for v in verify.values())
(ROOT / 'Receipts' / 'material_usage_flags.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('SVD_MATERIAL_FLAGS ' + json.dumps({'all_ok': report['all_ok'], 'verify': verify}, default=str))
