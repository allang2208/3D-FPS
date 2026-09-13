"""Finish only the weather-library merge after the first save met a file lock."""
import unreal as u, json
from pathlib import Path

O=Path(__file__).parent
D='/Game/Weapons/M1911/Tactical20260913'
E=u.EditorAssetLibrary
auth=json.loads((O/'authoring.json').read_text())
reference='/Game/Weapons/M1911/RearFinish20260913/Materials/M_M1911_RearUnified_Steel'
report={'parts':{},'dry_to_wet':{},'weather_libraries':{}}
for kind,info in auth.items():
    report['parts'][kind]={'mesh':D+'/'+kind+'/SM_TacticalDevice.SM_TacticalDevice',
        'body_material':D+'/Materials/M_M1911_'+kind+'_Body.M_M1911_'+kind+'_Body',
        'collar_material':D+'/Materials/M_M1911_Tactical_Collar.M_M1911_Tactical_Collar',
        'coating_uv':1,'physical_tile_m':.1,'reference_material':reference,'emitter_author_ue_cm':info['emitter_ue_cm']}
for name in ['M_M1911_Tactical_Collar','M_M1911_laser_Body','M_M1911_flashlight_Body']:
    dry=D+'/Materials/'+name+'.'+name
    wet=u.load_asset(D+'/Wet/M_Wet_'+name)
    if wet is None:raise RuntimeError('Missing authored wet material '+name)
    report['dry_to_wet'][dry]=wet.get_path_name()
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path)
    mapping=dict(library.get_editor_property('wet_materials'))
    mapping.update({dry:u.load_asset(wet) for dry,wet in report['dry_to_wet'].items()})
    library.set_editor_property('wet_materials',mapping)
    if not E.save_loaded_asset(library,False):raise RuntimeError('Cannot save weather mappings '+path)
    report['weather_libraries'][path]='Merged three M1911 tactical material mappings'
    u.log('M1911_TACTICAL_RAIN_LIBRARY_SAVED '+path)
(O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M1911_TACTICAL_RAIN_REGISTRATION_COMPLETE')
