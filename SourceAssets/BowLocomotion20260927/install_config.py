"""Activate only successfully saved locomotion clips, preserving fresh parallel edits."""
import json
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
saved=json.loads((P/'import-receipt.json').read_text(encoding='utf8'))['saved']
roles=('Walk','Run','LoadedWalk','LoadedRun','LoadedIdle')
for role in roles:
    if 'A_Bow_'+role not in saved:raise RuntimeError('Clip not yet saved: '+role)
prefix='/Game/Weapons/DarkBow20260925/LocomotionV23/A_Bow_'
path=ROOT/'Content/ColdSteelData/bows.json'
data=json.loads(path.read_text(encoding='utf-8-sig'));bow=data['bow_dark']
changed=bow.get('bow_locomotion_prefix')!=prefix
bow['bow_locomotion_prefix']=prefix
bow['bow_presentation_revision']=max(33,int(bow.get('bow_presentation_revision',0))+int(changed))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=ROOT/'Config/DefaultGame.ini';text=path.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/LocomotionV23")'
if line not in text:
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:raise RuntimeError('Packaging section missing')
    path.write_text(text.replace(section,section+'\n'+line,1),encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'revision':bow['bow_presentation_revision'],
    'prefix':prefix,'assets':saved,'gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_LOCOMOTION_ACTIVATED revision='+str(bow['bow_presentation_revision']))
