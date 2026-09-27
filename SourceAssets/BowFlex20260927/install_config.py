"""Activate saved V15 presentation assets without changing combat statistics."""
from pathlib import Path
import json, hashlib
P=Path(__file__).parent; ROOT=P.parents[1]; DATA=ROOT/'Content/ColdSteelData'
r=json.loads((P/'import-receipt.json').read_text()); saved=r['saved']
roles=('Original','Swift','Heavy','Steady')
keys=('bow_flex_distribution','bow_release_return_seconds','bow_release_ring_seconds','bow_feedback_scale')
values={'Original':(1.15,.032,.17,1.),'Swift':(.9,.027,.13,.75),'Heavy':(1.45,.040,.20,1.25),'Steady':(.7,.033,.145,.8)}
def visual(role):
    return dict(bow_part_riser_mesh=saved['SK_Bow_Flex_'+role],bow_part_riser_material='',bow_part_riser_scale=1.,**dict(zip(keys,values[role])))
for role in roles:
    for prefix in ('SK_Bow_Flex_','M_Bow_Flex_'):
        if prefix+role not in saved: raise RuntimeError('Asset not saved '+prefix+role)
for role in ('Idle','Ready','Equip','Nock','Draw','Hold','Release','Run'):
    if 'A_Bow_'+role not in saved: raise RuntimeError('Animation not saved '+role)
path=DATA/'bows.json'; data=json.loads(path.read_text(encoding='utf-8-sig')); bow=data['bow_dark']
bow.update(visual('Original')); bow['bow_animation_prefix']='/Game/Weapons/DarkBow20260925/ElasticV15/A_Bow_'
bow['bow_presentation_revision']=max(26,bow.get('bow_presentation_revision',0))
if '拉弓时按 R 缓收弓' not in bow['desc']: bow['desc']+='拉弓时按 R 缓收弓，箭留在弦上。'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=DATA/'bow-gunsmith.json'; data=json.loads(path.read_text(encoding='utf-8-sig'))
riser=next(c for c in data['columns'] if c['key']=='riser'); riser['factory_visual'].update(visual('Original'))
for option in riser['options']:
    role={'swift_limb':'Swift','heavy_limb':'Heavy','steady_limb':'Steady'}.get(option['id'])
    if role: option['visual'].update(visual(role))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=ROOT/'Config/DefaultGame.ini'; text=path.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/ElasticV15")'
if line not in text:
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text: raise RuntimeError('Missing packaging section')
    path.write_text(text.replace(section,section+'\n'+line,1),encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'revision':bow['bow_presentation_revision'],'bodies':{x:visual(x) for x in roles},'animation_prefix':bow['bow_animation_prefix'],'gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_ELASTIC_V15_ACTIVATED')
