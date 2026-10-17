"""Read back saved revision tags, source hashes and asset paths; no gameplay run."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;A=json.loads((O/'authoring.json').read_text(encoding='utf-8'));L=u.EditorAssetLibrary
report={'completed':False,'animations':{},'surfaces':{},'runtime_tested':False}
for role,entry in A['clips'].items():
 path='/Game/Weapons/M870/Tactical20261015/Animations/A_M870_'+role
 clip=L.load_asset(path)
 if not clip:raise RuntimeError('Missing saved animation '+path)
 author=L.get_metadata_tag(clip,'M870AnimationAuthor');source=L.get_metadata_tag(clip,'M870AnimationSourceSHA256');expected=hashlib.sha256(Path(entry['file']).read_bytes()).hexdigest()
 report['animations'][role]={'path':path,'author':author,'source_hash':source,'expected_source_hash':expected,'length':clip.get_play_length()}
 if author!='M870LeftArm20261016' or source!=expected:raise RuntimeError('Saved animation source differs: '+path)
for path in ('/Game/Weapons/M870/Tactical20261015/SK_M870_V7','/Game/Weapons/M870/Arms20261016/SK_M870_BareArmsV7'):
 asset=L.load_asset(path)
 if not asset:raise RuntimeError('Missing saved surface '+path)
 revision=L.get_metadata_tag(asset,'M870LeftElbowSurface')
 if revision!='20261016':raise RuntimeError('Saved surface revision differs: '+path)
 report['surfaces'][path]={'revision':revision,'path':asset.get_path_name()}
report['completed']=True
(O/'saved_assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M870_SAVED_ASSET_READBACK',len(report['animations']),'animations',len(report['surfaces']),'surfaces',flush=True)
