"""Build and save species-specific corpses, then attach their cooked bindings."""
from pathlib import Path
import json
import shutil
import sys
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpse_materials

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/MonsterSoftCorpse20261005'
DEST = '/Game/Monsters/SoftCorpseV1'
E = u.EditorAssetLibrary
report = dict(complete=False, saved=[], characters=[], tested=False, rendered=False)


def record():
    (ROOT/'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


def save(asset):
    if not asset or not E.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save '+str(asset))
    report['saved'].append(asset.get_path_name()); record()


def main():
    for item in json.loads((ROOT/'sources.json').read_text(encoding='utf8')):
        key = item['key']; folder = DEST+'/'+key
        source = u.load_asset(item['source'])
        # Preserve the production package before adding metadata. No live geometry edits.
        source_file = PROJECT/'Content'/(item['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
        backup = ROOT/'Before'/source_file.relative_to(PROJECT/'Content')
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(source_file, backup)
        mesh = u.load_asset(item['corpse'])
        skeleton_path = folder+'/SKEL_'+key+'_SoftCorpse'
        skeleton = u.load_asset(skeleton_path) or E.duplicate_asset(item['skeleton'], skeleton_path)
        data_path = folder+'/DA_'+key+'_SoftCorpse'
        data = u.load_asset(data_path)
        if not data:
            factory = u.DataAssetFactory(); factory.set_editor_property('data_asset_class', u.M14SoftBodyData)
            data = u.AssetToolsHelpers.get_asset_tools().create_asset('DA_'+key+'_SoftCorpse', folder, u.M14SoftBodyData, factory)
        if data.get_editor_property('corpse_mesh') != mesh:
            # Only corpse LOD0 is rebound. The source keeps all authored LODs;
            # never allow a corpse to switch to an unrebound legacy LOD.
            count = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh)
            if count > 1:
                if not u.SkeletalMeshEditorSubsystem.remove_lods(mesh, list(range(1, count))):
                    raise RuntimeError('Could not remove legacy corpse LODs '+key)
            if not u.M14SoftBodyData.build_corpse(mesh, skeleton, data, str(ROOT/key/'cage.json'), str(ROOT/key/'embedding.bin')):
                raise RuntimeError('Could not bind corpse '+key)
        slots = list(source.get_editor_property('materials'))
        materials = set()
        for slot in slots:
            slot.set_editor_property('material_interface', corpse_materials.make(slot.get_editor_property('material_interface'), materials))
        mesh.set_editor_property('materials', slots)
        report['saved'].extend(sorted(materials))
        save(mesh); save(skeleton); save(data)
        u.M14SoftBodyData.bind_to_living_mesh(source, data)
        save(source)
        report['characters'].extend(item['characters']); record()
        print('SOFT_CORPSE_INSTALLED '+key, flush=True)
    report.update(complete=True, standard='M14 V19 continuous XPBD death',
                  excluded_humanoids=['NurseZombie', 'FatZombie', 'SpitterZombie', 'Mutant3', 'WitchRebuilt', 'BlindSupplicantM07', 'HundredEyedSlag'],
                  m14_weakpoint='maw and descendants, shared critical-hit contract', user_testing_pending=True)
    record()


try:
    main()
except Exception as error:
    report['error'] = str(error); record(); raise
