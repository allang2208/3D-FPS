"""Material-only revision: keep accepted mesh geometry, transforms, sockets and scale untouched."""
from pathlib import Path
import runpy,json,datetime
import unreal as u
ns=runpy.run_path(str(Path(__file__).parent/'install.py'),run_name='anvil_aged_material')
path=ns['SURF']+'/Materials/M_AnvilReferenceSteel'
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('The anvil material has unsaved editor changes; preserve them')
old=u.load_asset(path)
archive=ns['SURF']+'/Materials/M_AnvilReferenceSteel_BrightV3Archive'
if old and not u.EditorAssetLibrary.does_asset_exist(archive):
    copy=u.EditorAssetLibrary.duplicate_asset(path,archive)
    if not copy or not u.EditorAssetLibrary.save_loaded_asset(copy,False):raise RuntimeError('Cannot retain previous surface')
worked={k:u.load_asset(ns['SURF']+'/Textures/T_Anvil_Worked_'+k) for k in ('BaseColor','ORM','Normal')}
mat=ns['material'](worked)
receipt={'surface_revision':'AgedIron4','saved':ns['saved'],'previous_surface':archive,
    'changes':['dark oxidized iron','irregular worn zones using existing scanned metal mask',
               'higher roughness and reduced bright steel coverage','reduced oxide specular'],
    'mesh_reimported':False,'mesh_edited':False,'runtime_tested':False,'rendered':False}
out=Path(__file__).parent/'Receipts'/('aged-material-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
out.write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('ANVIL_AGED_MATERIAL_SAVED '+json.dumps(receipt),flush=True)
