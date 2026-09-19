import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
paths={'optic':'/Game/Weapons/M4Holographic/SM_M4_Holographic','drum':'/Game/Weapons/M4Drum/SM_M4_LargeDrum','prism':'/Game/Weapons/PrismHandstopV1/SM_PrismHandstop','angled':'/Game/Weapons/M4AngledForegripCompact75/SM_M4_AngledForegrip'}
for k in ['suppressor','brake','titanium_brake']:paths[k]='/Game/Weapons/M4MuzzlesV1/SM_M4_'+k
out={}
for k,p in paths.items():
 m=u.load_asset(p);assert m,p
 out[k]={'asset':p,'source':m.get_editor_property('asset_import_data').get_first_filename(),'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in m.get_editor_property('static_materials')]}
(O/'sources.json').write_text(json.dumps(out,indent=2));u.log('AKM_ATTACHMENT_SOURCE_PASS')
