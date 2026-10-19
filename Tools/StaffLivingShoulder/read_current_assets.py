"""Read saved employee asset references without rendering or re-exporting geometry."""
import unreal as u,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/StaffLivingShoulder20261017')
report={}
for role in ['FemaleA','FemaleB']:
 bp=u.load_asset('/Game/Monsters/StaffLiving/BP_LivingStaff'+role)
 cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh');comp=cdo.get_editor_property('mesh')
 row={'bp':bp.get_path_name(),'mesh':mesh.get_path_name(),'component_mesh':comp.get_editor_property('skeletal_mesh_asset').get_path_name(),'skeleton':mesh.get_editor_property('skeleton').get_path_name(),'physics':mesh.get_editor_property('physics_asset').get_path_name(),'materials':[],'clips':{},'import_sources':list(mesh.get_editor_property('asset_import_data').extract_filenames())}
 for m in mesh.get_editor_property('materials'):
  mat=m.material_interface;row['materials'].append({'path':mat.get_path_name(),'blend_mode':str(mat.get_editor_property('blend_mode')),'two_sided':mat.get_editor_property('two_sided')})
 for key in ['idle','walk','attack']:row['clips'][key]=cdo.get_editor_property(key+'_clip').get_path_name()
 report[role]=row
(OUT/'Diagnosis/current_assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SHOULDER_ASSET_REFERENCES_READ',json.dumps(report),flush=True)
