"""Save the bound M-09 Blueprint against the updated native Editor module."""
from pathlib import Path
import json
import unreal as u

root=Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/StepsHurtV11')
record=json.loads((root/'asset_receipt.json').read_text(encoding='utf-8'))
bp=u.load_asset('/Game/Monsters/BellowSacLobber/BP_BellowSacLobber')
defaults=u.get_default_object(bp.generated_class())
sounds=dict(defaults.get_editor_property('bellow_sounds'))
for role,path in record['saved_sounds'].items():
    sound=u.load_asset(path)
    if not sound: raise RuntimeError('Missing authored sound '+path)
    sounds[u.Name(role)]=sound
defaults.set_editor_property('bellow_sounds',sounds)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):
    raise RuntimeError('Could not save M-09 after updating its native module')
record['post_native_build_blueprint_saved']=True
(root/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('BELLOW_STEPS_HURT_V11_NATIVE_BOUND: existing and new audio retained; no playback.',flush=True)
