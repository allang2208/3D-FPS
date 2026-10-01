import json
from pathlib import Path
O=Path(__file__).parent
materials=json.loads((O/'import_receipt.json').read_text())
icons=json.loads((O/'icon_import_receipt.json').read_text())
presentation=json.loads((O/'current_presentation.json').read_text())
result={'weapon':'ue_hk416','cause':'Laser_Grip and Flash_Light PBR atlas assignments were reversed.',
 'corrected_atlases':{'Laser_Grip':'Accs_1004','Flash_Light':'Accs_1001'},
 'saved_materials':materials['saved'],'saved_icon_count':len(icons['saved']),
 'editable_and_fbx_parts':['vertical','flashlight','laser'],'geometry_or_uv_changed':False,
 'material_binding_inspected':materials['complete'],'offline_comparison_reviewed':True,
 'comparison_before':'materials_before.png','comparison_after':'materials_after.png',
 'runtime_after_tested':False,'existing_game_equipped_hk416':presentation['screenshot_requested'],
 'editor_or_game_started':False,'native_code_changed':False}
(O/'completion.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
