import unreal,json
from pathlib import Path
path='/Game/Weapons/M4Replacement/Candidate/SM_M4_Assembled_Candidate'
m=unreal.load_asset(path)
assert isinstance(m,unreal.StaticMesh),path
slots=m.get_editor_property('static_materials')
assert len(slots)>0
report={'asset':m.get_path_name(),'materials':[s.get_editor_property('material_interface').get_path_name() if s.get_editor_property('material_interface') else None for s in slots],'runtime_replaced':False}
assert all(report['materials'])
Path('D:/FPS3D/FPSGAME/SourceAssets/M4Replacement/ue_candidate_readback.json').write_text(json.dumps(report,indent=2))
unreal.log('M4_READBACK_OK '+json.dumps(report))
