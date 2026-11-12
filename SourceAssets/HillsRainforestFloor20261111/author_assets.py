"""Import the Quixel moss and jungle scans and update only the two ground masters and grass master."""
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
BATCH=ROOT/'SourceAssets/HillsRainforestFloor20261111'
BASE='/Game/WorldGeneration/TemperateHills'
TEXTURES=BASE+'/WetForest/Textures'
materials=[BASE+'/M_TemperateGround',BASE+'/PebbleShore/M_PebbleShoreGround',BASE+'/Grass/M_TemperateMeadow']
sources={
    'T_RainforestMoss_':json.loads((BATCH/'Receipts/source-download.json').read_text(encoding='utf-8')),
    'T_JungleGround_':json.loads((BATCH/'Receipts/jungle-download.json').read_text(encoding='utf-8'))}
paths=materials+[TEXTURES+'/'+prefix+s for prefix in sources for s in ('BaseColor','Normal','ARH')]
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Preserve unsaved targets: '+str(dirty.intersection(paths)))
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
report={'saved':[],'backups':[],'map_modified':False,'runtime_tested':False,
        'sources':sources}
for path in paths:
    source=ROOT/'Content'/(path[6:]+'.uasset')
    if source.exists():
        dest=BATCH/'Backups'/('Assets-'+stamp)/(path[6:]+'.uasset')
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest)
        report['backups'].append(str(dest))

def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj

def save(obj):
    if isinstance(obj,u.Material):
        errors=L.recompile_material(obj)
        if errors:raise RuntimeError('Material compilation request failed: '+str(errors))
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Unable to save '+obj.get_path_name())
    report['saved'].append(obj.get_path_name())

def import_texture(prefix,source,kind,compression,srgb):
    name=prefix+kind
    task=u.AssetImportTask()
    task.set_editor_property('filename',str(BATCH/'Textures'/(name+'.png')))
    task.set_editor_property('destination_path',TEXTURES)
    task.set_editor_property('destination_name',name)
    task.set_editor_property('automated',True)
    task.set_editor_property('replace_existing',True)
    task.set_editor_property('save',False)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=load(TEXTURES+'/'+name)
    tex.set_editor_property('compression_settings',compression)
    tex.set_editor_property('srgb',srgb)
    tex.set_editor_property('max_texture_size',2048)
    tex.set_editor_property('never_stream',False)
    E.set_metadata_tag(tex,'Quixel.ScanId',source['scan_id'])
    E.set_metadata_tag(tex,'Quixel.FabListing',source['listing'])
    save(tex)

for prefix,source in sources.items():
    for kind,compression,srgb in (
            ('BaseColor',u.TextureCompressionSettings.TC_DEFAULT,True),
            ('Normal',u.TextureCompressionSettings.TC_NORMALMAP,False),
            ('ARH',u.TextureCompressionSettings.TC_MASKS,False)):
        import_texture(prefix,source,kind,compression,srgb)

spec=importlib.util.spec_from_file_location('forest_wet_materials',ROOT/'Tools/WorldGeneration/forest_wet_materials.py')
wet=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wet)
for path in materials[:2]:
    mat=load(path);wet.apply_ground(mat);save(mat)
grass=load(materials[2]);wet.apply_grass(grass);save(grass)
report['finished_at']=datetime.now().astimezone().isoformat()
(BATCH/'Receipts/assets-authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('HILLS_RAINFOREST_FLOOR_SAVED '+str(len(report['saved'])))
