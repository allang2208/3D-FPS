"""Read saved source revision and duration for the two reload assets."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent
A=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
result={}
for role,entry in A['clips'].items():
    path='/Game/Weapons/M870/Tactical20261015/Animations/A_M870_'+role
    clip=u.load_asset(path)
    if not clip:raise RuntimeError('Missing saved '+path)
    result[role]={'path':path,'length':clip.get_play_length(),'expected_length':entry['duration'],'author':u.EditorAssetLibrary.get_metadata_tag(clip,'M870AnimationAuthor'),'source_hash':u.EditorAssetLibrary.get_metadata_tag(clip,'M870AnimationSourceSHA256'),'expected_source_hash':hashlib.sha256(Path(entry['file']).read_bytes()).hexdigest()}
(O/'saved_animations.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('M870_SOURCE_RELOAD_SAVE_READBACK',json.dumps(result),flush=True)
