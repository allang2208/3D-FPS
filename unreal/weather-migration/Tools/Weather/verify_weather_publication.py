"""Read-only asset-presence check after recoverable legacy rain retirement."""
import json
from pathlib import Path
import unreal

rows=[]
for name in ['NS_FPS_RainFine','NS_FPS_SurfaceSplashes','NS_FPS_RainMist','NS_FPS_RoofDrips']:
    path='/Game/Weather/VFX/'+name
    asset=unreal.load_asset(path)
    assert isinstance(asset,unreal.NiagaraSystem),path
    rows.append({'asset':path,'class':asset.get_class().get_name()})
for name in ['M_RainStreak','M_RainDroplet','M_RainMist','M_RainWetSurface','MPC_FPS_Weather']:
    path='/Game/Weather/Materials/'+name
    assert unreal.EditorAssetLibrary.does_asset_exist(path),path
for name in ['NS_FPS_Rain','NS_FPS_RainSplashes']:
    assert not unreal.EditorAssetLibrary.does_asset_exist('/Game/Weather/VFX/'+name),name
out=Path(unreal.Paths.project_saved_dir())/'StormClouds'/'publication-assets.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'passed':True,'systems':rows,'legacy_assets_absent':True},indent=2)+'\n',encoding='utf-8')
unreal.log('WEATHER_PUBLICATION_ASSETS_PASS')
