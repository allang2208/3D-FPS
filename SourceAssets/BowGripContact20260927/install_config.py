"""Activate saved fitted grip; merge only the original grip's catalog fields."""
import json,shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
saved=json.loads((P/'import-receipt.json').read_text())['saved']['SM_Bow_GripWrap_Fitted']
old='/Game/Weapons/DarkBow20260925/ModularV13/SM_Bow_GripWrap.SM_Bow_GripWrap'
backup=ROOT/'Saved/BowGripContact20260927/Before'
def read(relative):
    path=ROOT/relative;dest=backup/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(path,dest)
    return path,json.loads(path.read_text(encoding='utf-8-sig'))
path,data=read('Content/ColdSteelData/bows.json');bow=data['bow_dark']
if bow['bow_part_grip_mesh'] not in (old,saved):raise RuntimeError('Preserving another default grip assignment')
changed=bow['bow_part_grip_mesh']!=saved
bow['bow_part_grip_mesh']=saved
bow['bow_presentation_revision']=max(32,int(bow['bow_presentation_revision'])+int(changed))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path,data=read('Content/ColdSteelData/bow-gunsmith.json')
for column in data['columns']:
    if column['key']=='grip':
        field=column['factory_visual']
        if field['bow_part_grip_mesh'] not in (old,saved):raise RuntimeError('Preserving another factory grip assignment')
        field['bow_part_grip_mesh']=saved
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
path=ROOT/'Config/DefaultGame.ini';dest=backup/'Config/DefaultGame.ini';dest.parent.mkdir(parents=True,exist_ok=True)
if not dest.exists():shutil.copy2(path,dest)
text=path.read_text(encoding='utf-8-sig');line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/GripContactV22")'
if line not in text:
    section='[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:raise RuntimeError('Packaging section missing')
    path.write_text(text.replace(section,section+'\n'+line,1),encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'mesh':saved,'revision':bow['bow_presentation_revision'],'gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_GRIP_CONTACT_ACTIVATED',saved)
