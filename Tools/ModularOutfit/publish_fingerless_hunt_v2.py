"""Import matching pickup, then switch only the existing brown glove item."""
import json,shutil
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
DEST='/Game/Characters/ModularOutfit20260924/FingerlessHuntV2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt=json.loads((ROOT/'asset-receipt.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Finish every native glove import before publishing')
for path in [receipt['material'],*receipt['profiles'].values()]:
    if not E.does_asset_exist(path):raise RuntimeError('Missing '+path)
icon=P/'Content/ColdSteelData/Icons/ModularOutfit20260924/ue_field_gloves_fingerless.png'
if not icon.is_file():raise RuntimeError('Missing production inventory icon')
name='SM_FingerlessHunt_Pickup';folder=DEST+'/Pickups';path=folder+'/'+name
task=u.AssetImportTask();task.filename=str(ROOT/(name+'.fbx'));task.destination_name=name;task.destination_path=folder
task.automated=True;task.replace_existing=True;task.save=False
opts=u.FbxImportUI();opts.set_editor_property('import_as_skeletal',False);opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
opts.set_editor_property('automated_import_should_detect_type',False);opts.set_editor_property('import_materials',False);opts.set_editor_property('import_textures',False)
opts.get_editor_property('static_mesh_import_data').set_editor_property('combine_meshes',True);task.options=opts
E.make_directory(folder);A.import_asset_tasks([task]);mesh=u.load_asset(path);mat=u.load_asset(receipt['material'])
if not mesh or not mat:raise RuntimeError('Missing imported pickup/material')
mesh.set_material(0,mat);mesh.modify()
if not (u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outer()],False) or E.save_loaded_asset(mesh,False)):raise RuntimeError('Cannot save pickup')
cfgpath=P/'Content/ColdSteelData/modular_outfits.json';itempath=P/'Content/ColdSteelData/items.json'
cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'));items=json.loads(itempath.read_text(encoding='utf-8-sig'))
old=cfg['items']['ue_field_gloves']
if set(old['rig_meshes'])!=set(receipt['profiles']):raise RuntimeError('Brown rig profile set changed during production')
before=ROOT/'before-publication.json'
if not before.exists():before.write_text(json.dumps(dict(recipe=old,item=items['ue_field_gloves']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
old['rig_meshes']=receipt['profiles'];old['material']=receipt['material'];old['covers']=[]
item=items['ue_field_gloves'];item['name']='棕色露指皮革手套'
item['desc']='五指从指根露出，皮革覆盖掌心与手背，短腕口和指根边缘采用薄卷边与缝线。保留裸手触感，复用当前手型与动作，可与衣袖独立搭配。'
item['ue_icon']='Icons/ModularOutfit20260924/ue_field_gloves_fingerless.png';item['world_mesh']=mesh.get_path_name();item['world_material']=receipt['material']
cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
itempath.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
changed_animations=set()
for stage in ('FingerClearance','SavedFingerRefinement','CuffArmClearance','CuffShoulderClearance'):
    saved=ROOT/stage/'installed.json'
    if saved.exists():changed_animations.update(json.loads(saved.read_text()))
(ROOT/'published.json').write_text(json.dumps(dict(item='ue_field_gloves',profiles=len(receipt['profiles']),material=receipt['material'],pickup=mesh.get_path_name(),
    covers=[],animations_changed=len(changed_animations),runtime_tested=False),indent=2)+'\n')
print('FINGERLESS_PUBLISHED',len(receipt['profiles']),mesh.get_path_name(),flush=True)
