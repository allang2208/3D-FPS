"""Finalize saved Zhenmo Niagara bytecode in a fresh authoring process.

The external stack edits can leave a valid but empty compiled system cached.
Force the engine's graph invalidation on load, compile, then save only this asset.
"""
from pathlib import Path
import json,shutil
import unreal as u

OUT=Path(__file__).resolve().parent
PATH='/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold'

def rebuild():
    if u.find_object(None,PATH+'.NS_ZhenmoRisingGold'):
        raise RuntimeError('Rebuild Zhenmo runtime in a fresh commandlet before this system is loaded')
    file=Path(u.Paths.project_dir())/'Content'/(PATH.removeprefix('/Game/')+'.uasset')
    before=OUT/'Before'/'NS_ZhenmoRisingGold-pre-runtime-rebuild.uasset'
    before.parent.mkdir(parents=True,exist_ok=True)
    if not before.exists():shutil.copy2(file,before)
    old=u.SystemLibrary.get_console_variable_int_value('fx.ForceCompileOnLoad')
    setter=u.ConsoleVariablesEditorFunctionLibrary.set_console_variable_by_name_int
    if not setter('fx.ForceCompileOnLoad',1):raise RuntimeError('Cannot enable forced Niagara load compilation')
    try:
        system=u.load_asset(PATH)
        if not system or not u.RainAssetEditor.compile_rain(system):
            raise RuntimeError('Zhenmo forced compilation failed')
    finally:
        setter('fx.ForceCompileOnLoad',old)
    u.EditorAssetLibrary.set_metadata_tag(system,'Zhenmo.RuntimeCompile','Fresh-process forced graph rebuild after stack authoring, 2026-10-06')
    if not u.EditorAssetLibrary.save_loaded_asset(system,False):raise RuntimeError('Cannot save Zhenmo runtime bytecode')
    (OUT/'runtime_compile_receipt.json').write_text(json.dumps({'asset':system.get_path_name(),'saved':True,'force_compile_on_load':True,'runtime_verified':False},indent=2),encoding='utf-8')
    print('ZHENMO_RUNTIME_REBUILT '+system.get_path_name(),flush=True)

if __name__=='__main__':rebuild()
