"""Record completed authoring, imports and native build receipts without running tests."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text(encoding='utf-8-sig'))
saved=read('import_receipt.json');geometry=read('exports.json');registration=read('registration_receipt.json')
delivery={
 'name':'陨星熔核','id':'meteor_core','weapon':'ue_steel_warhammer','slot':'hammer_heads','tier':'legendary','exclusive':True,
 'editable_source':'MeteorCore_Detailed_Editable.blend','mesh':registration['mesh'],
 'triangles':geometry['parts'][0]['triangles'],'editable_components':geometry['editable_components'],
 'runes':geometry['rune_count'],'through_windows':geometry['cage_window_count'],
 'assets_saved':saved['complete'],'saved_asset_count':len(saved['assets']),
 'commandlet':read('commandlet_receipt.json'),'registration':registration,
 'emission':saved['lava_effect'],'animated_material_source':'lava_emission.hlsl',
 'icon':'Icons/meteor_core.png','icon_prompt':'icon-prompt.txt','icon_method':'actual model grayscale source + built-in image_gen framing',
 'native_builds':{target:read(target+'-build-receipt.json') for target in ('game','editor')},
 'numerical_balance_assigned':False,'editor_launched_by_this_task':False,
 'game_tested':False,'visual_acceptance_tested':False
}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('METEOR_CORE_DELIVERY_RECORDED',flush=True)
