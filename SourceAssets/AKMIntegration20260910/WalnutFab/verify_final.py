import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/WalnutFab'
lib=u.MaterialEditingLibrary
mesh=u.load_asset(P+'/SK_AKM_MannyNative');mi=u.load_asset(P+'/MI_AKM_RedBrownWalnut');assert mesh and mi
value=lib.get_material_instance_vector_parameter_value(mi,'RedBrownTint');assert abs(value.r-.8)<.001 and abs(value.g-.38)<.001,str(value)
slots=mesh.get_editor_property('materials');assert any(str(s.material_slot_name)=='M_AKMR_Walnut' and s.material_interface==mi for s in slots)
report=json.loads((O/'applied.json').read_text());report['tint']=[.8,.38,.25];report['mesh']=mesh.get_path_name()
report['materials']=[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in slots]
(O/'applied.json').write_text(json.dumps(report,indent=2));u.log('AKM_WALNUT_FINAL_BINDING_PASS')
