"""Apply the existing beech opacity-pin repair to only its three active materials."""
import json, runpy, shutil
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/HillsClosure20261118/BeechMaterial'
BASE='/Game/Items/HarvestTimber/Beech/'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
OUT.mkdir(parents=True,exist_ok=True)

def backup(path):
    rel=path.split('.')[0].removeprefix('/Game/')
    for ext in ('.uasset','.uexp','.ubulk'):
        source=ROOT/'Content'/(rel+ext)
        target=OUT/'Before'/(rel+ext)
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    return asset

for name in ('M_FallingBeech','MI_FallingBeech_Bark','MI_FallingBeech_Foliage'):backup(BASE+name)
author=runpy.run_path(str(ROOT/'SourceAssets/BeechHarvestOreFix20261110/install_assets.py'))
rebuild=author['master_material']
rebuild.__globals__['backup']=backup
rebuild.__globals__['save']=save
master=rebuild()
saved=[master.get_path_name()]
for part in ('Bark','Foliage'):
    instance=u.load_asset(BASE+'MI_FallingBeech_'+part)
    if not instance or instance.get_editor_property('parent')!=master:raise RuntimeError('Unexpected beech parent')
    L.update_material_instance(instance)
    saved.append(save(instance).get_path_name())
(OUT/'saved.json').write_text(json.dumps({'saved':saved,'tree_meshes_modified':False,'map_modified':False},indent=2),encoding='utf-8')
u.log('HILLS_BEECH_MATERIAL_SAVED')
