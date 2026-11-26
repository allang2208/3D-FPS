"""Task-scoped static contracts; complements rather than replaces the C++ audit."""
import hashlib
import json
from pathlib import Path

P=Path(__file__).resolve().parents[2]
out=P/'SourceAssets/PlantingGameplay20261022'
rules=json.loads((P/'Content/ColdSteelData/planting_rules.json').read_text(encoding='utf-8'))
models=json.loads((P/'Content/ColdSteelData/crop_models_v3.json').read_text(encoding='utf-8'))
items=json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
checks=[]
def check(name,value):
    checks.append({'name':name,'passed':bool(value)})

check('only final V3 model catalog',models['model_version']=='V3')
check('four crop choices',set(c['id'] for c in rules['crops'])=={'tomato','potato','carrot','wheat'})
check('input/output definitions exist',all(c['input_item'] in items and c['output_item'] in items for c in rules['crops']))
check('positive explicit configurable defaults',all(c['input_count']>0 and c['output_count']>0 and c['growth_seconds']>0 for c in rules['crops']) and rules['defaults_are_development_tuning_not_user_specified'])
paths=[path for c in models['crops'].values() for v in c['variants'].values() for path in v['stages'].values()]
check('36 unique model stages exist on disk',len(paths)==len(set(paths))==36 and all((P/'Content'/path.split('.')[0].removeprefix('/Game/')).with_suffix('.uasset').exists() for path in paths))
source=P/rules['slot_source'];original=json.loads(source.read_text(encoding='utf-8-sig'))
check('authored bed manifest provenance',hashlib.sha256(source.read_bytes()).hexdigest()==rules['slot_source_sha256'])
expected=[[s['position_m'][0]*100,-s['position_m'][1]*100,s['position_m'][2]*100] for s in original['plant_slots']]
check('16 authored roots converted to correct UE axes',rules['slots_cm']==expected and len(expected)==16)
widget=(P/'Source/FPSGAME/UI/ColdSteelWorkbenchWidget.cpp').read_text(encoding='utf-8-sig')
plant_ui=(P/'Source/FPSGAME/UI/ColdSteelPlantingWorkbench.cpp').read_text(encoding='utf-8-sig')
check('same workbench shell and public theme', 'SetPlantingMode(Planting)' in widget and 'ColdSteelUI::ButtonStyle' in plant_ui and 'CraftingBodyContent' in plant_ui)
check('same combobox row widget and selected/hover style', 'GenerateRecipeOption' in plant_ui and 'PlantingChoice->SetItemStyle(ItemStyle)' in widget)
check('normal crafting handler remains behind mode guard','if(bPlantingMode){HandlePlantingAction();return;}' in widget and 'Crafting->Craft(SelectedRecipe,N,Reason)' in widget)
profile=(P/'Source/FPSGAME/UI/ColdSteelInventoryTypes.h').read_text(encoding='utf-8-sig')
system=(P/'Source/FPSGAME/Building/ColdSteelPlantingSystem.cpp').read_text(encoding='utf-8-sig')
check('inventory and crops in one existing profile commit','UPROPERTY() TArray<FColdSteelCropPlant> PlantingCrops;' in profile and 'M->CommitState(MoveTemp(Proposed))' in system)
check('asynchronous bounded mesh catalog','RequestAsyncLoad(Paths' in system and 'MeshCache.Num()==36' in system and 'LoadSynchronous' not in system)
check('stage mesh switching never rerolls variants','Plant.Variant=FName' in system and system.count('FRandomStream Random(')==1)
check('stale or duplicate plant identity checked','ExpectedPlantId' in system and '植株状态已变化' in system)
check('crop packages included in cook configuration','+DirectoriesToAlwaysCook=(Path="/Game/Props/Crops/V3")' in (P/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig'))
report={'checks':len(checks),'failures':sum(not c['passed'] for c in checks),'results':checks,'cpp_compiled_by_this_check':False,'ui_rendered':False,'game_started':False}
(out/'static-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
if report['failures']:raise SystemExit(1)
