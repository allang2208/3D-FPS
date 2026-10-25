"""Save six isolated native waist variants per batch; resume by source hash."""
import gc, hashlib, importlib.util, json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentWaist20261023'
DEST='/Game/Characters/ModularOutfit20260924/GarmentWaist20261023'
if (R/'authoring.lock').exists():raise RuntimeError('Waist authoring revision is in progress; saved assets retained')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('Retain current PIE; defer waist asset writes')
spec=importlib.util.spec_from_file_location('garment_waist_writer',str(P/'Tools/GarmentSleeveRepair/save_assets.py'))
io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
authored=read(R/'authored.json');receipt_path=R/'saved_assets.json'
receipt=read(receipt_path) if receipt_path.exists() else dict(saved={},runtime_tested=False)
receipt['completed']=False;write(receipt_path,receipt);count=0
for row in authored['records']:
    key=row['item']+'/'+row['group']+'/'+row['profile'];old=receipt['saved'].get(key)
    if old and old['author_sha256']==row['author_sha256'] and u.EditorAssetLibrary.does_asset_exist(old['asset']):continue
    if count>=6:break
    if sha(row['file'])!=row['author_sha256']:raise RuntimeError('Author input changed: '+key)
    native=P/'Content'/(row['source_asset'].split('.')[0][6:]+'.uasset')
    if sha(native)!=row['source_sha256']:raise RuntimeError('Native garment changed: '+key)
    io.R=R/'Fits'/row['signature'];io.DEST=DEST+'/'+row['signature'];io.receipt_path=io.R/'saved_assets.json'
    io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
    io.write_mesh(dict(item=row['item'],profile=row['profile'],file=row['source_file']))
    receipt['saved'][key]=io.receipt['saved'][row['item']+'/'+row['profile']]
    write(receipt_path,receipt);count+=1;gc.collect();u.SystemLibrary.collect_garbage()
receipt['completed']=all(receipt['saved'].get(r['item']+'/'+r['group']+'/'+r['profile'],{}).get('author_sha256')==r['author_sha256'] for r in authored['records'])
if receipt['completed']:
    # As in PantsCompatibility, persist UE's post-load LOD section normalization.
    for row in authored['records']:
        path=receipt['saved'][row['item']+'/'+row['group']+'/'+row['profile']]['asset']
        mesh=u.load_asset(path);mesh.modify()
        if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Cannot finish LOD sections: '+path)
        mesh=None;gc.collect();u.SystemLibrary.collect_garbage()
write(receipt_path,receipt);print('GARMENT_WAIST_SAVED',len(receipt['saved']),len(authored['records']),receipt['completed'],flush=True)
