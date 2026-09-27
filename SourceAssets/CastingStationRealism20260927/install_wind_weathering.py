"""Save furnace-matched station finishes and the five meshes needed for moving tools."""
from pathlib import Path
import datetime
import importlib
import json
import runpy
import sys
import unreal as u

root=Path(u.Paths.project_dir())
here=root/'SourceAssets/CastingStationRealism20260927'
sys.path.insert(0,str(here))
import materials
importlib.reload(materials)
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop play before replacing station finishes; play was not stopped')
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
destination='/Game/Props/CastingStation20260926'
if any(p.startswith(destination+'/') for p in dirty):
    raise RuntimeError('Preserving unsaved casting station assets')

runpy.run_path(str(here/'read_furnace_style.py'),run_name='__main__')
saved=[]
for name in ('M_BlackenedAnvil','M_WorkedAnvil','MI_DarkForgedIron','M_OakDry','M_OakBarrel'):
    path=materials.DEST+'/'+name
    backup=materials.DEST+'/BeforeWindV7/'+name
    if E.does_asset_exist(path) and not E.does_asset_exist(backup):
        copy=E.duplicate_asset(path,backup)
        if not copy or not E.save_loaded_asset(copy,False):
            raise RuntimeError('Unable to preserve previous finish '+path)

for asset in materials.build_surfaces().values():
    if isinstance(asset,u.Material):
        errors=L.recompile_material(asset)
        if errors:raise RuntimeError('Material compile failed '+asset.get_path_name()+': '+str(errors))
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    saved.append(asset.get_path_name())

runpy.run_path(str(here/'install_tool_rack.py'),run_name='__main__')
receipt={'materials_saved':saved,'wind_source':'FluidPresentationSubsystem::WindWithGustAt',
    'geometry':'four rigid tools pivoting on their eye-to-hook contact; fixed rack and hooks',
    'furnace_materials_modified':False,'water_modified':False,
    'runtime_tested':False,'rendered':False}
(here/('wind-weathering-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')).write_text(
    json.dumps(receipt,indent=2),encoding='utf-8')
print('CASTING_WIND_WEATHERING_SAVED '+json.dumps(receipt),flush=True)
