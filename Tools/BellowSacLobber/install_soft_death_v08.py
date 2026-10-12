"""Save Bellow's own corpse mesh/skeleton/material/data and bind its actual living mesh."""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BellowSacLobberMeshy20261012/SoftDeathV08'
DEST = '/Game/Monsters/BellowSacLobber/V08/SoftDeath'
sys.path.insert(0, str(PROJECT / 'Tools/MonsterSoftCorpse'))
import corpse_materials
corpse_materials.DEST = DEST + '/Materials'
E = u.EditorAssetLibrary
report = dict(complete=False, saved=[], tested=False, rendered=False,
              standard='M14 V19 continuous XPBD', display_name='鼓囊 M-09')


def record():
    (ROOT / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def save(asset):
    if not asset or not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + str(asset))
    report['saved'].append(asset.get_path_name())
    record()


def main():
    item = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))[0]
    targets = (DEST, item['source'].split('.')[0])
    if any(p.get_path_name().startswith(targets) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Target corpse or living mesh has unsaved changes')
    source = u.load_asset(item['source'])
    source_file = PROJECT / 'Content' / (item['source'].split('.')[0].removeprefix('/Game/') + '.uasset')
    backup = ROOT / 'Before' / source_file.relative_to(PROJECT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(source_file, backup)
    mesh = u.load_asset(item['corpse'])
    skeleton_path = DEST + '/SKEL_BellowSacLobber_SoftCorpse'
    skeleton = u.load_asset(skeleton_path) or E.duplicate_asset(item['skeleton'], skeleton_path)
    data_path = DEST + '/DA_BellowSacLobber_SoftCorpse'
    data = u.load_asset(data_path)
    if not data:
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.M14SoftBodyData)
        data = u.AssetToolsHelpers.get_asset_tools().create_asset('DA_BellowSacLobber_SoftCorpse', DEST, u.M14SoftBodyData, factory)
    if data.get_editor_property('corpse_mesh') != mesh:
        count = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh)
        if count > 1 and not u.SkeletalMeshEditorSubsystem.remove_lods(mesh, list(range(1, count))):
            raise RuntimeError('Cannot remove legacy unbound corpse LODs')
        folder = ROOT / item['key']
        if not u.M14SoftBodyData.build_corpse(mesh, skeleton, data, str(folder / 'cage.json'), str(folder / 'embedding.bin')):
            raise RuntimeError('Bellow corpse binding failed')

    # The native authoring step classifies nodes from the cooked source weights;
    # internal node structs are deliberately not exposed through Python.
    anatomy = json.loads((ROOT / item['key'] / 'anatomy.json').read_text(encoding='utf-8'))
    unsupported = list(data.get_editor_property('unsupported_nodes'))
    if not unsupported or not data.get_editor_property('collapse_in_place'):
        raise RuntimeError('Native authoring did not apply the Bellow support-release profile')
    materials = set()
    slots = list(source.get_editor_property('materials'))
    for slot in slots:
        slot.set_editor_property('material_interface', corpse_materials.make(slot.get_editor_property('material_interface'), materials))
    mesh.set_editor_property('materials', slots)
    report['saved'].extend(sorted(materials))
    save(mesh)
    save(skeleton)
    save(data)
    u.M14SoftBodyData.bind_to_living_mesh(source, data)
    save(source)
    report.update(complete=True, source_mesh=source.get_path_name(), corpse_mesh=mesh.get_path_name(),
                  data=data.get_path_name(), blueprint=item['blueprint'], animation_set_preserved=item['animation_set'],
                  anatomy=anatomy, unsupported_node_indices=unsupported, unsupported_nodes=len(unsupported), collapse_in_place=True,
                  handoff='AWolfMonster.EnterState: current visible pose on server and clients',
                  native_changes='Optional anatomical release fields in corpse authoring only', user_testing_pending=True)
    record()
    print('BELLOW_SOFT_DEATH_V08_INSTALLED ' + data.get_path_name())


try:
    main()
except Exception as error:
    report['error'] = str(error)
    record()
    raise
