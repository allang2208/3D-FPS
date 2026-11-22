from pathlib import Path
import json,hashlib
import unreal as u
W=Path(__file__).resolve().parent
R=Path('D:/FPS3D/FPSGAME')
P=R/'SourceAssets/ThunderGodHammer20261028/ChargeRestoreV6'
D='/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1'
job=json.loads((W/'job.json').read_bytes());k=job['targets'][0];name=k.rsplit('/',1)[1]
if Path(u.Paths.project_dir()).resolve()!=(W/'Host').resolve():raise RuntimeError('Expected private host')
if hashlib.sha256(Path(job['source']).read_bytes()).hexdigest()!=job['source_sha256']:raise RuntimeError('FBX changed')
old=u.load_asset(k)
if not old or not u.EditorAssetLibrary.get_metadata_tag(old,'ThunderThrowRevision').startswith('ThrowRefineV5:'):raise RuntimeError('Unexpected existing charge')
motion={'clips':[name]}
receipt={'saved':[]}
def record():pass
source=P/'import_assets.py';txt=source.read_text(encoding='utf8')
start=txt.index('arms = u.load_asset');end=txt.index("receipt['complete'] = True",start)
exec(compile(txt[start:end],str(source),'exec'),globals())
if len(receipt['saved'])!=1 or receipt['saved'][0].partition('.')[0]!=k:raise RuntimeError('Wrong saved asset')
clip=u.load_asset(k);model=clip.get_editor_property('data_model_interface')
info=dict(fbx=job['source'],sha256=job['source_sha256'],revision=u.EditorAssetLibrary.get_metadata_tag(clip,'ThunderThrowRevision'),frames=model.get_number_of_frames(),seconds=clip.get_play_length(),rate_scale=clip.get_editor_property('rate_scale'))
if info['frames']!=480 or abs(info['seconds']-2)>0.00001 or info['rate_scale']!=1.:raise RuntimeError('Unexpected V6 motion timeline '+str(info))
(W/'saved.json').write_text(json.dumps({k:info},indent=2))
print('GUAN_LEI_V6_CHARGE_SAVED',info['frames'],info['seconds'])
