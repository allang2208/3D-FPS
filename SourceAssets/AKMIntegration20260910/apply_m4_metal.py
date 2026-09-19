import unreal,json
from pathlib import Path
O=Path(__file__).parent
dest='/Game/Weapons/AKMIntegration/Materials/SK_AKM_MannyNative'
mesh=unreal.load_asset(dest) if unreal.EditorAssetLibrary.does_asset_exist(dest) else unreal.EditorAssetLibrary.duplicate_asset('/Game/Weapons/AKMIntegration/Native/SK_AKM_MannyNative',dest)
m4=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
source={str(s.material_slot_name):s.material_interface for s in m4.get_editor_property('materials')}
mapping={'M_AKMR_BluedSteel':'Body_001','M_AKMR_BoltSteel':'Body_001','M_AKMR_Parkerized':'Flash_Hider_001'}
slots=mesh.get_editor_property('materials');report=[]
for i,s in enumerate(slots):
 name=str(s.material_slot_name)
 if name in mapping:s.material_interface=source[mapping[name]];slots[i]=s
 report.append({'slot':name,'material':s.material_interface.get_path_name()})
mesh.set_editor_property('materials',slots);assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
(O/'m4_metal_binding.json').write_text(json.dumps(report,indent=2));unreal.log('AKM_M4_METAL_BIND_PASS')
