"""Persist fresh Niagara runtime bytecode after authoring; does not play FX."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
ASSET='/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold'
# ConsoleVariablesEditor has no populated command cache in a commandlet.
# The process-local -ForceDPCVars flag sets Niagara's real CVar before loading.
if u.SystemLibrary.get_console_variable_int_value('fx.ForceCompileOnLoad')!=1:
    raise RuntimeError('Launch this authoring process with -ForceDPCVars=fx.ForceCompileOnLoad=1')
if u.find_object(None,ASSET+'.NS_ZhenmoRisingGold'):
    raise RuntimeError('Fresh compile requires the target system to be unloaded')
system=u.load_asset(ASSET)
if not system or not u.RainAssetEditor.compile_rain(system):
    raise RuntimeError('Zhenmo runtime bytecode compilation failed')
u.EditorAssetLibrary.set_metadata_tag(system,'Zhenmo.RuntimeCompile','GroundVisibility20261007 fresh forced graph compilation')
if not u.EditorAssetLibrary.save_loaded_asset(system,False):
    raise RuntimeError('Cannot save recompiled Zhenmo runtime bytecode')
path=OUT/'asset_receipt.json'
data=json.loads(path.read_text(encoding='utf-8'))
data['niagara_fresh_compile_pending']=False
data['niagara_fresh_compile_saved']=True
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('ZHENMO_VISIBILITY_RUNTIME_SAVED',flush=True)
