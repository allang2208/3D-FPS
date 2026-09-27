"""Activate only the saved nocking overrides; retain V15 flex and combat tuning."""
import json
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
saved=json.loads((P/'import-receipt.json').read_text(encoding='utf8'))['saved']
changes={key:saved['A_Bow_'+role] for key,role in [('bow_nock_animation','Nock'),('bow_draw_entry_animation','QuickNock'),('bow_chain_entry_animation','ChainNock')]}
path=ROOT/'Content/ColdSteelData/bows.json';data=json.loads(path.read_text(encoding='utf-8-sig'));bow=data['bow_dark']
bow.update(changes);bow['bow_presentation_revision']=max(27,bow.get('bow_presentation_revision',0))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=ROOT/'Config/DefaultGame.ini';text=path.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/NockFlowV16")'
if line not in text:
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:raise RuntimeError('Packaging section missing')
    path.write_text(text.replace(section,section+'\n'+line,1),encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'revision':bow['bow_presentation_revision'],'overrides':changes,'draw_entry_seconds':bow['bow_draw_entry_seconds'],'gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_NOCK_FLOW_V16_ACTIVATED')
