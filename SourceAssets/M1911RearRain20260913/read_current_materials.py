"""Read only the active weapon material sources and current weather library."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;E=u.EditorAssetLibrary
paths={'M1911':['/Game/Weapons/M1911/Hero20260913/SK_M1911_Manny'],
       'QBZ191':['/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny']}
dirs={'M1911':['/Game/Weapons/M1911/Attachments20260913/Meshes'],
      'QBZ191':['/Game/Weapons/QBZ191/Attachments20260913','/Game/Weapons/RearGripFinish20260913/QBZ191','/Game/Weapons/ResonanceGrip20260913/Repaired91871/QBZ191','/Game/Weapons/TacticalDevices20260913/QBZ191']}
report={'weapons':{},'weather_libraries':{}}
for family in paths:
    candidates=list(paths[family])
    for directory in dirs[family]:
        for p in E.list_assets(directory,recursive=True,include_folder=False):
            data=E.find_asset_data(p)
            if str(data.asset_class_path.asset_name)=='StaticMesh':candidates.append(p)
    report['weapons'][family]={}
    for p in candidates:
        mesh=u.load_asset(p)
        if not mesh:raise RuntimeError(p)
        slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
        report['weapons'][family][mesh.get_path_name()]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]
for p in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    da=u.load_asset(p)
    if da:report['weather_libraries'][p]={'mapping':{str(k):v.get_path_name() for k,v in da.get_editor_property('wet_materials').items()}}
(O/'sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M1911_QBZ191_MATERIAL_SOURCES_READ')
