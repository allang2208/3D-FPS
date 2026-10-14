"""Save only Blizzard's clearance-aware world cloud; preserve the held V3 cloud.

Background asset authoring, with existing materials as read-only sources.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, save
from build_fireball_flames import FLOAT, VEC3, POSITION
from build_fireball_flight import user_parameter, expression
from build_blizzard_charged_v3 import cloud_layer, cloud_lifecycle, CLOUD_LAYERS

DEST = '/Game/Skills/Blizzard/ClearanceV4'
EAL = u.EditorAssetLibrary


def build_cloud():
    if any(str(p.get_path_name()).startswith(DEST)
           for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved Blizzard ClearanceV4 packages')
    EAL.make_directory(DEST)
    path = DEST + '/NS_BlizzardStormCloud'
    source = '/Game/Skills/Blizzard/ChargedV3/NS_BlizzardStormCloud'
    system = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    material = u.load_asset('/Game/Skills/Blizzard/ChargedV3/MI_BlizzardStormCloud')
    if not system or not material:
        raise RuntimeError('Restore Blizzard ChargedV3 sources first')
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
    for key, typ in [('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3),
                     ('SurfaceNormal', VEC3), ('Wind', VEC3), ('RadiusX', FLOAT),
                     ('RadiusY', FLOAT), ('CloudHeight', FLOAT), ('CloudThickness', FLOAT),
                     ('StormDuration', FLOAT), ('CloudEmission', FLOAT),
                     ('Strength', FLOAT), ('DetailReduction', FLOAT)]:
        user_parameter(system, key, typ)
    expression(system, '', 'SystemUpdateScript', 'SystemState', 'Loop Duration',
               'max(.6,User.StormDuration+.6)')
    lifecycle = cloud_lifecycle()
    for count, (name, level, color) in zip([18, 14, 9, 8], CLOUD_LAYERS):
        cloud_layer(system, material, name, count, level, color, lifecycle, False)
    system.set_editor_property('fixed_bounds',
                              u.Box(min=u.Vector(-1200, -1200, -80), max=u.Vector(1200, 1200, 1400)))
    save(system)
    receipt = {'saved_asset': system.get_path_name(), 'core_particles': 49,
               'clearance_parameter': 'User.CloudThickness',
               'sprite_alignment': 'SurfaceNormal', 'gameplay_tested': False, 'rendered': False}
    folder = ROOT / 'Saved/BlizzardFix20261012'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('BLIZZARD_CLEARANCE_V4_SAVED ' + json.dumps(receipt))
    return system


if __name__ == '__main__':
    build_cloud()
