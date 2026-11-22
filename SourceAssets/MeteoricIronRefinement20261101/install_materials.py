"""Replace only meteor mode 5 on both current rune masters; preserve other modes."""
from pathlib import Path
import runpy
import json,shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
REV='MeteoricIron20261101V2'
DEST='/Game/Weapons/AzureRunesword20260913/MeteoricIronRefinement20261101'
MASTERS=['/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
 '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold']
if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('PIE is running; preserve the user session.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    path=package.get_path_name()
    if path in MASTERS or path.startswith(DEST):raise RuntimeError('Unsaved target package '+path)

task=u.AssetImportTask()
task.filename=str(P/'T_MeteoricCrystalFieldV2.png');task.destination_path=DEST
task.destination_name='T_MeteoricCrystalFieldV2';task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(DEST+'/'+task.destination_name)
if not texture:raise RuntimeError('Crystal field import failed')
for key,value in [('srgb',False),('compression_settings',u.TextureCompressionSettings.TC_BC7),
                  ('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD),('never_stream',False),
                  ('address_x',u.TextureAddress.TA_CLAMP),('address_y',u.TextureAddress.TA_CLAMP)]:
    texture.set_editor_property(key,value)
if not E.save_loaded_asset(texture,False):raise RuntimeError('Crystal field save failed')

apply_graph=runpy.run_path(str(P/'finish_graph.py'))['apply']
saved=[]
for path in MASTERS:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing current material '+path)
    if E.get_metadata_tag(mat,'MeteoricIronRefinementRevision')==REV:
        saved.append({'asset':path,'already_current':True});continue
    asset=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/asset.relative_to(ROOT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(asset,backup)
    apply_graph(mat, texture)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Meteor material compilation failed '+str(errors))
    E.set_metadata_tag(mat,'MeteoricIronRefinementRevision',REV)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+path)
    saved.append({'asset':path,'saved':True,'mode':5})
appearance='深灰半精抛剑面浮现细密晶片，随光线转动显出银灰层次，刃口清亮。'
for filename in ['melee-gunsmith.json','rune-sword-modules.json']:
    path=ROOT/'Content/ColdSteelData'/filename
    before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if filename=='melee-gunsmith.json':
        options=next(c for c in data['columns'] if c['key']=='blade_material')['options']
        next(o for o in options if o['id']=='meteoric_iron')['description']=appearance
    else:data['slots']['blade_material']['meteoric_iron']['appearance']=appearance
    backup=P/'BeforeCatalog'/filename;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Catalog changed during merge '+filename)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'material-receipt.json').write_text(json.dumps({'revision':REV,'materials':saved,'texture':texture.get_path_name(),
    'gameplay_tested':False,'preview_rendered':False,'icon_updated':False},indent=2)+'\n',encoding='utf8')
print('METEORIC_REFINEMENT_SAVED',json.dumps(saved))
