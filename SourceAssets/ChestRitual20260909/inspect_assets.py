import json
from pathlib import Path
import unreal as u
out=Path(__file__).parent
d=json.loads((out/'import_report.json').read_text());mesh=u.EditorAssetLibrary.load_asset(d['mesh']);rows=[]
for sm in mesh.get_editor_property('materials'):
 mat=sm.get_editor_property('material_interface')
 rows.append({'slot':str(sm.get_editor_property('material_slot_name')),'material':mat.get_path_name() if mat else None,'name':mat.get_name() if mat else None})
report={'mesh_slots':rows,'materials':[]}
for name,path in d['materials'].items():
 mi=u.EditorAssetLibrary.load_asset(path);parent=mi.get_editor_property('parent')
 report['materials'].append({'key':name,'path':path,'parent':parent.get_path_name(),'skeletal':parent.get_editor_property('used_with_skeletal_mesh'),'tint':str(u.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi,'MetalTint')),'roughness':u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,'RoughnessBase')})
(out/'asset_inspection.json').write_text(json.dumps(report,indent=2));u.log('RITUAL_INSPECTION '+json.dumps(report))
