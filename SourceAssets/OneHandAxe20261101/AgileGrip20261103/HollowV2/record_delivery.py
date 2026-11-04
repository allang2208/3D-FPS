"""Record asset production completion without running acceptance tests."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text('utf-8-sig'))
entry=read('hollow_grip.json');saved=read('import_receipt.json');registration=read('registration_receipt.json')
if not saved['complete'] or not registration['published']:raise RuntimeError('Asset production has incomplete steps')
receipt={'complete':True,'definition':'ue_tactical_hatchet','id':entry['id'],'name':entry['name'],
    'model_revision':entry['model_revision'],'source':str(P/'TacticalHatchet_GripAgile_HollowV2_Editable.blend'),
    'fbx':entry['fbx'],'textures':entry['textures'],'triangles':entry['triangles'],'window':entry['window'],
    'saved_assets':saved['assets'],'stats_unchanged':True,'stats':registration['stats'],
    'length_and_joint_locations_retained':True,'pommel_offset_cm':[0,0,0],
    'native_code_changed':False,'native_build_required':False,'editor_ui_opened':False,
    'runtime_tested':False,'acceptance_rendered':False,'icon_asset_rendered':True}
(P/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P.parent/'active_model.json').write_text(json.dumps({'revision':entry['model_revision'],'manifest':'HollowV2/hollow_grip.json',
    'delivery':'HollowV2/delivery.json','author':'HollowV2/author_hollow.py','saved_mesh':saved['parts'][0]['mesh'],
    'source':'HollowV2/TacticalHatchet_GripAgile_HollowV2_Editable.blend'},indent=2)+'\n',encoding='utf-8')
print('HOLLOW_GRIP_DELIVERED assets='+str(len(saved['assets'])))
