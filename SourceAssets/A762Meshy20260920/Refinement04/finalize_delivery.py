"""Record the completed stock authoring and UE import operations."""
import json
from datetime import datetime
from pathlib import Path
O=Path(__file__).parent
receipt=json.loads((O/'import.json').read_text(encoding='utf-8')) if (O/'import.json').exists() else {}
delivery={
 'asset':'A762','revision':'StockJoint04','updated_at':datetime.now().astimezone().isoformat(),
 'status':receipt.get('status','exported_waiting_for_import'),
 'runtime_mesh':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
 'editable_source':'A762_StockJoint_Editable.blend','exports':'Exports',
 'changes':['continuous twin-rod tail shoulders','closed tail support and curved backing plate',
            'complete ribbed rubber pad and clean material seam','explicit exported material partitions'],
 'geometry_parameters':'authoring.json','engine_receipt':'import.json',
 'backup_assets':receipt.get('backups',{}),'runtime_assets':receipt.get('meshes',{}),
 'animations_changed':False,'skeleton_rest_changed':False,'sights_changed':False,
 'native_code_changed':False,'audio':'existing AKM sounds unchanged',
 'tests_run':False,'pie_started':False,'acceptance_rendered':False,'user_acceptance':'pending'
}
(O/'DELIVERY.json').write_text(json.dumps(delivery,indent=2,ensure_ascii=False),encoding='utf-8')
if receipt.get('status')=='imported_and_saved':
    p=O.parent/'DELIVERY.json';main=json.loads(p.read_text(encoding='utf-8'))
    main['latest_refinement']='Refinement04/DELIVERY.json';main['integration_editable_source']='Refinement04/A762_StockJoint_Editable.blend'
    p.write_text(json.dumps(main,indent=2,ensure_ascii=False),encoding='utf-8')
print('A762 StockJoint04 delivery: '+delivery['status'])
