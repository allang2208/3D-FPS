"""Repair the exact material defects captured by the hills runtime audit."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'Saved/HillsDisappearanceAudit20261114/MaterialRepair'
BASE = '/Game/WorldGeneration/TemperateHills'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary

def backup(path):
    relative = path.split('.')[0].removeprefix('/Game/')
    for ext in ('.uasset','.uexp','.ubulk'):
        source = ROOT/'Content'/(relative+ext)
        target = OUT/'Before'/(relative+ext)
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    return asset.get_path_name()

def recompile(material):
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError(material.get_path_name()+': '+str(list(errors)))

def repair_fungi_instancing():
    path = BASE+'/EcologyUpgrade/Fungi/pdvv2_tier_2/Materials/MI_pdvv2'
    instance = u.load_asset(path)
    if not instance:
        raise RuntimeError('Missing active fungal material '+path)
    target = BASE+'/EcologyUpgrade/Fungi/Materials/M_ForestFungiGLTF'
    parent = instance.get_editor_property('parent')
    if parent.get_path_name().split('.')[0] not in ('/InterchangeAssets/gltf/Substrate/M_GLTF',target):
        raise RuntimeError('Fungal parent changed; preserve it: '+parent.get_path_name())
    backup(path)
    backup(target)
    # Keep the engine Interchange material untouched. All six active fungal
    # variants share this instance and retain their existing glTF parameters.
    master = u.load_asset(target) if E.does_asset_exist(target) else E.duplicate_asset(parent.get_path_name(),target)
    if not master:
        raise RuntimeError('Cannot create project-owned fungal material')
    master.set_editor_property('used_with_instanced_static_meshes',True)
    master.set_editor_property('used_with_nanite',True)
    recompile(master)
    L.set_material_instance_parent(instance,master)
    L.update_material_instance(instance)
    return [save(master),save(instance)]

def repair_underfoot_usage():
    saved = []
    for name in ('M_ForestTwig01','M_ForestTwig02','M_MossyForestBoulder'):
        path = BASE+'/WetForest/Underfoot/'+name
        backup(path)
        material = u.load_asset(path)
        if not material:
            raise RuntimeError('Missing '+path)
        material.set_editor_property('used_with_nanite',True)
        material.set_editor_property('used_with_instanced_static_meshes',True)
        recompile(material)
        saved.append(save(material))
    return saved

def main():
    project = Path(u.Paths.project_dir()).resolve()
    isolated = ROOT/'Saved/HillsDisappearanceAudit20261114/MaterialHost'
    if project!=ROOT.resolve() and not (
            project==isolated.resolve() and
            '-HillsAuditMaterialRepair' in u.SystemLibrary.get_command_line() and
            (project/'Content').resolve()==(ROOT/'Content').resolve()):
        raise RuntimeError('Use the FPSGAME project or the exact isolated audit material host')
    OUT.mkdir(parents=True,exist_ok=True)
    saved = repair_underfoot_usage()
    saved.extend(repair_fungi_instancing())
    beech = '/Game/Items/HarvestTimber/Beech/'
    for name in ('M_FallingBeech','MI_FallingBeech_Bark','MI_FallingBeech_Foliage'):
        backup(beech+name)
    author = runpy.run_path(str(ROOT/'SourceAssets/BeechHarvestOreFix20261110/install_assets.py'))
    rebuild = author['master_material']
    # Preserve the original full-import receipt; this repair has its own backups
    # and receipt and only invokes one authoring function.
    rebuild.__globals__['backup'] = backup
    rebuild.__globals__['save'] = save
    # Rebuild only the existing cut/fade wrapper. Do not reimport tree meshes,
    # stump profiles or the map from the full authoring script.
    master = rebuild()
    saved.append(master.get_path_name())
    for part in ('Bark','Foliage'):
        instance = u.load_asset(beech+'MI_FallingBeech_'+part)
        if instance.get_editor_property('parent')!=master:
            raise RuntimeError('Unexpected beech material parent')
        L.update_material_instance(instance)
        saved.append(save(instance))
    (OUT/'saved.json').write_text(json.dumps({'saved':saved,'map_saved':False},indent=2),encoding='utf8')
    u.log('HILLS_AUDIT_MATERIALS_SAVED '+str(len(saved)))

if __name__=='__main__':
    main()
