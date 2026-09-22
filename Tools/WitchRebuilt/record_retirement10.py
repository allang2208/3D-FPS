from pathlib import Path
import json
root=Path('D:/FPS3D/FPSGAME');source=root/'SourceAssets/WitchRebuilt20260921';out=source/'Revision10'
archived=json.loads((out/'asset_retirement_result.json').read_text(encoding='utf-8'))
native=json.loads((root/'Docs/AssetArchives/witch-variants-native-20260922.json').read_text(encoding='utf-8'))
result={'sole_witch_id':'WitchRebuilt','display_name':'巫婆·重建候选','class':'/Script/FPSGAME.WitchRebuiltMonster',
 'removed_catalog_ids':['Witch','WitchFoundation'],'combat_base':'AWitchMonster retained as abstract shared gameplay',
 'archived_ue_packages':archived['retired_packages'],'archived_native_files':len(native),
 'retained':'Current WitchRebuilt plus required Foundation templates, original appearance textures, staff and authoring sources',
 'build_log':'Saved/BuildEditor/build-20260922-175034.log','runtime_tested':False,'visual_tested':False}
(out/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
p=source/'ue_delivery.json';delivery=json.loads(p.read_text(encoding='utf-8'));delivery.update(status='WitchRebuilt is the sole selectable Witch; retired variants archived; user gameplay testing pending',revision10=result)
p.write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
print('Recorded sole Witch delivery: '+str(len(archived['retired_packages']))+' retired packages, '+str(len(native))+' retired source files')
