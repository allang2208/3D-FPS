import json
from datetime import datetime
from pathlib import Path
O=Path(__file__).parent
receipt=json.loads((O/'import.json').read_text(encoding='utf-8'))
delivery={
 'asset':'A762','revision':'ExteriorRefinement01','updated_at':datetime.now().astimezone().isoformat(),
 'status':receipt['status'],'runtime_mesh':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
 'editable_source':'A762_Refined_Editable.blend','export_directory':'Exports',
 'changes':['true rear aperture and separate front sight post','regular rail slots','exterior barrel and gas tube sections','stock tubes','open muzzle exterior','bounded retained-surface refinement','per-part PBR finish','split normals and MikkTSpace tangents'],
 'geometry_and_material_parameters':'authoring.json','engine_receipt':'import.json',
 'backup_assets':receipt['backups'],'runtime_assets':receipt['meshes'],
 'animations_changed':False,'skeleton_rest_changed':False,'audio':'existing AKM audio reused unchanged',
 'native_code_changed':False,'native_compile_required':False,
 'tests_run':False,'pie_started':False,'acceptance_rendered':False,'user_acceptance':'pending'
}
(O/'DELIVERY.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rootfile=O.parent/'DELIVERY.json';root=json.loads(rootfile.read_text(encoding='utf-8'))
root['latest_refinement']='Refinement01/DELIVERY.json';root['integration_editable_source']='Refinement01/A762_Refined_Editable.blend';root['tested']=False
rootfile.write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A762 refinement delivery recorded: '+receipt['status'])
