"""Activate the saved continuous nocking clips, retaining camera and combat tuning."""
import json,shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
saved=json.loads((P/'import-receipt.json').read_text(encoding='utf8'))['saved']
changes={key:saved['A_Bow_'+role] for key,role in [
    ('bow_nock_animation','Nock'),('bow_draw_entry_animation','QuickNock'),('bow_chain_entry_animation','ChainNock')]}
path=ROOT/'Content/ColdSteelData/bows.json'
data=json.loads(path.read_text(encoding='utf-8-sig'));bow=data['bow_dark']
changed=any(bow.get(k)!=v for k,v in changes.items())
revision=max(31,int(bow.get('bow_presentation_revision',0))+int(changed))
bow.update(changes)
bow['bow_nock_keeps_draw_pose']=1
bow['bow_presentation_revision']=revision
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=ROOT/'Config/DefaultGame.ini';text=path.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/NockContinuityV21")'
if line not in text:
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:raise RuntimeError('Packaging section missing')
    path.write_text(text.replace(section,section+'\n'+line,1),encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'revision':revision,'overrides':changes,
    'draw_entry_seconds':bow['bow_draw_entry_seconds'],'loaded_ready_matches_draw':True,
    'nock_seconds':bow['nock_seconds'],'gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_NOCK_CONTINUITY_V21_ACTIVATED revision='+str(revision))
