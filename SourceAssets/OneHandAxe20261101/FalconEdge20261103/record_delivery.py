"""Record completed production steps, without running acceptance checks."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text('utf-8-sig'))
build=read('build_receipt.json');assets=read('import_receipt.json');registered=read('registration_receipt.json')
if build['exit_code']!=0 or not assets['complete'] or not registered['published']:
    raise RuntimeError('Production pipeline has an incomplete step')
entry=read('falcon_edge.json');design=read('design.json')
receipt={'complete':True,'definition':design['weapon'],'id':design['id'],'name':design['name'],'slot':design['slot'],
    'modification_tier':'Special','stats':design['stats'],'model_source':str(P/'TacticalHatchet_FalconEdge_Editable.blend'),
    'fbx':entry['fbx'],'triangles':entry['triangles'],'textures':entry['textures'],'saved_assets':assets['assets'],
    'model_recipe':'Content/ColdSteelData/tactical-hatchet-modules.json',
    'option_catalog':'Content/ColdSteelData/tactical-hatchet-gunsmith.json',
    'native_build':build,'editor_ui_opened':False,'runtime_tested':False,'acceptance_rendered':False,
    'icon_asset_rendered':True,'image_generation':'built-in image_gen; exact inputs and prompt recorded in icon_manifest.json',
    'notes':'Existing animations, hand rules and modification persistence reused. No gameplay, network or visual acceptance test run.'}
(P/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FALCON_EDGE_DELIVERED assets='+str(len(assets['assets'])))
