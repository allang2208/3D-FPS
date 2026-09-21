"""Write delivery records from the authoring/import operation receipts."""
import json
from pathlib import Path
from datetime import datetime
O=Path(__file__).parent
receipt=json.loads((O/'import.json').read_text(encoding='utf-8')) if (O/'import.json').exists() else {}
delivery={
 'asset':'A762','revision':'ADSSurfaces03','updated_at':datetime.now().astimezone().isoformat(),
 'status':receipt.get('status','exported_waiting_for_import'),
 'runtime_mesh':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
 'editable_source':'A762_ADS_Surfaces_Editable.blend','exports':'Exports',
 'changes':['open protective cheeks and independent rear aperture leaf from new close reference',
            'complete recessed handguard shell, continuous upper side covers and backed front ribs',
            'continuous receiver roof, rear shoulders and stock sockets with controlled split normals',
            'bounded cleanup of retained receiver side planes with UV0 and structural normals preserved'],
 'backup_assets':receipt.get('backups',{}),'runtime_assets':receipt.get('meshes',{}),
 'geometry_parameters':'authoring.json','engine_receipt':'import.json',
 'front_sight_changed':False,'magazine_changed':False,'animations_changed':False,
 'skeleton_rest_changed':False,'native_code_changed':False,'native_compile_required':False,
 'audio':'existing AKM sounds unchanged','tests_run':False,'pie_started':False,
 'acceptance_rendered':False,'user_acceptance':'pending'
}
(O/'DELIVERY.json').write_text(json.dumps(delivery,indent=2,ensure_ascii=False),encoding='utf-8')
if receipt.get('status')=='imported_and_saved':
    p=O.parent/'DELIVERY.json';root=json.loads(p.read_text(encoding='utf-8'))
    root['integration_editable_source']='Refinement03/A762_ADS_Surfaces_Editable.blend'
    root['latest_refinement']='Refinement03/DELIVERY.json'
    p.write_text(json.dumps(root,indent=2,ensure_ascii=False),encoding='utf-8')
print('A762 Refinement03 delivery: '+delivery['status'])
