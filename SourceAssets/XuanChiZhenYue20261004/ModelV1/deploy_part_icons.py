import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D=R/'Content/ColdSteelData/AttachmentIcons20260913';ID='ue_xuanchi_zhenyue'
guns=json.loads((R/'Content/ColdSteelData/melee-gunsmith.json').read_text(encoding='utf-8-sig'))
catalog=json.loads((R/'Content/ColdSteelData/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
jobs=[]
for slot in ['blade_1','guard','grip','pommel']:
    source=P/'Icons'/(slot+'_framed.png')
    if slot=='grip':source=P.parent/'FactoryIcons20261006/Icons/grip_factory_horizontal_framed.png'
    keys=[ID+'_category_'+slot,ID+'_'+slot+'_false']
    # Physical common modules use their shared framed icons. Only remaining
    # numerical adjustments retain the actual factory icon.
    if slot=='pommel':
        library=json.loads((D.parent/'shared-sword-pommels.json').read_text(encoding='utf-8-sig'))
        for option in library['options']:
            common=slot+'_'+option;file=D/(common+'.png')
            if file.exists():jobs.append({'source':str(file),'file':str(file),
                'asset':'/Game/ColdSteelData/AttachmentIcons20260913/'+common,'slot':slot})
    else:
        column=next(c for c in guns['columns'] if c['key']==slot)
        for o in column['options']:
            if o.get('weapons') and ID not in o['weapons']:continue
            common=slot+'_'+o['id'];file=D/(common+'.png')
            choices=catalog['slots'].get(slot,{})
            physical=o['id'] in choices and choices[o['id']]['mesh']!=choices['factory']['mesh']
            if physical and file.exists():
                jobs.append({'source':str(file),'file':str(file),'asset':'/Game/ColdSteelData/AttachmentIcons20260913/'+common,'slot':slot})
            else:keys.append(ID+'_'+slot+'_'+o['id'])
    for key in keys:
        dst=D/(key+'.png');shutil.copy2(source,dst)
        jobs.append({'source':str(source),'file':str(dst),'asset':'/Game/ColdSteelData/AttachmentIcons20260913/'+key,'slot':slot})
# Factory rune surface keeps the weapon's own cloud engraving, separate from blade I.
source=P.parent/'FactoryIcons20261006/Icons/blade_2_factory_framed.png'
key=ID+'_blade_2_false';dst=D/(key+'.png');shutil.copy2(source,dst)
jobs.append({'source':str(source),'file':str(dst),'asset':'/Game/ColdSteelData/AttachmentIcons20260913/'+key,'slot':'blade_2'})
# Blade II is the shared rune surface category, separate from physical blade I.
rune_category=D/'category_blade_2.png'
if not rune_category.exists():shutil.copy2(D/'ue_tang_dao_category_blade_2.png',rune_category)
jobs.append({'source':str(rune_category),'file':str(rune_category),
    'asset':'/Game/ColdSteelData/AttachmentIcons20260913/category_blade_2','slot':'blade_2'})
legendary=D/'ue_xuanchi_zhenyue_blade_2_zhenmo_rune.png'
if legendary.exists():jobs.append({'source':str(legendary),'file':str(legendary),
    'asset':'/Game/ColdSteelData/AttachmentIcons20260913/'+legendary.stem,'slot':'blade_2'})
(P/'Icons/deployments.json').write_text(json.dumps(jobs,indent=2));print('XUANCHI_PART_ICONS_DEPLOYED '+str(len(jobs)))
