"""Save measured waist pairs, one pair per editor batch; preserve original shirts."""
import gc,hashlib,importlib.util,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from pants_compatibility_paths import *
E=u.EditorAssetLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before saving pants compatibility assets')
spec=importlib.util.spec_from_file_location('pants_compatibility_native_writer',str(P/'Tools/GarmentSleeveRepair/save_assets.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
inventory=read(R/'inventory.json');authored=read(R/'authored.json');receipt_path=R/'saved_assets.json';receipt=read(receipt_path) if receipt_path.exists() else dict(saved={},runtime_tested=False)
receipt['completed']=False;write(receipt_path,receipt);processed=0
for row in authored['records']:
    key=row['signature']+'/'+row['profile'];old=receipt['saved'].get(key)
    if old and old['author_sha256']==row['author_sha256'] and E.does_asset_exist(old['asset']):continue
    if processed>=2:break
    if hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()!=row['author_sha256']:raise RuntimeError('Changed author source '+key)
    root=R/'Fits'/row['signature'];io.R=root;io.DEST=DEST+'/'+row['signature'];io.receipt_path=root/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
    field='owner_body_meshes' if row['profile']=='Owner_Jason' else 'rig_meshes';source=u.load_asset(inventory['shirt'][field]['Jason'])
    desc=root/'SaveInputs'/(row['profile']+'.json');write(desc,dict(materials=[m.material_interface.get_path_name() for m in source.materials],material_slots=[str(m.material_slot_name) for m in source.materials]))
    io.write_mesh(dict(profile=row['profile'],item='ue_field_sweater',file=str(desc)))
    receipt['saved'][key]=io.receipt['saved']['ue_field_sweater/'+row['profile']];write(receipt_path,receipt);processed+=1;source=None;gc.collect();u.SystemLibrary.collect_garbage()
receipt['completed']=all(receipt['saved'].get(r['signature']+'/'+r['profile'],{}).get('author_sha256')==r['author_sha256'] for r in authored['records'])
if receipt['completed']:
    # Persist the generated LOD section fixups after package reload.
    for record in receipt['saved'].values():
        asset=u.load_asset(record['asset']);asset.modify()
        if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot finish LOD sections')
        asset=None;gc.collect();u.SystemLibrary.collect_garbage()
write(receipt_path,receipt);print('PANTS_COMPATIBILITY_SAVED',len(receipt['saved']),len(authored['records']),receipt['completed'],flush=True)
