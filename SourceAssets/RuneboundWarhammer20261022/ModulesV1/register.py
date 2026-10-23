"""Publish the host fitting recipe; all accessory stats stay in shared libraries."""
import copy,json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
ID='ue_runebound_warhammer';D='/Game/Weapons/RuneboundWarhammer20261022/ModulesV1'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,obj):
    before=path.read_bytes() if path.exists() else None
    backup=P/'Before'/path.name
    if before is not None and not backup.exists():
        backup.parent.mkdir(exist_ok=True);backup.write_bytes(before)
    content=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    if before is not None and path.read_bytes()!=before:raise RuntimeError('Concurrent write: '+str(path))
    temporary=path.with_name(path.name+'.runebound-modules.tmp')
    temporary.write_text(content,encoding='utf-8');os.replace(temporary,path)

def publish():
    item=read(DATA/'items.json')[ID]
    old=read(DATA/'runebound-warhammer-modules.json')
    factory=read(P/'exports.json')['parts'];adapted=read(P/'adapted_exports.json')['parts']
    catalog={'version':2,'weapon':ID,'interface':'runebound_warhammer_modular_v1',
        'arms_mesh':item['tool_viewmodel'],'root_slot':'head_mount',
        'module_slots':[r['slot'] for r in factory], 'drive_bone':'WPN_root',
        'bone_mount':old['bone_mount'],'slots':{}}
    libraries={'hammer_heads':'common-hammer-heads.json','head_mount':'common-hammer-seats.json',
        'grip':'common-hammer-grips.json','pommel':'common-hammer-pommels.json'}
    appearances={slot:{o['id']:o['appearance'] for o in read(DATA/file)['options']} for slot,file in libraries.items()}
    for row in factory+adapted:
        slot=row['slot'];option=row['id'];package=D+'/'+row['mesh']
        spec={'mesh':package+'.'+row['mesh'],'location_cm':row['location_cm'],
            'appearance':('原装'+row['name']) if option=='factory' else appearances[slot][option]}
        if option!='factory':spec.update(interface='runebound_warhammer_modular_v1',
            shared_option_library=libraries[slot],model_revision='HostSectionFitV1',source_mesh=row['source_mesh'])
        catalog['slots'].setdefault(slot,{})[option]=spec
    common=read(DATA/'warhammer-modules.json')
    catalog['slots']['rune']=copy.deepcopy(common['slots']['rune'])
    catalog['slots']['rune']['factory']['appearance']='保留原生刻纹 · 不附加符文'
    # Retain any future host-specific additions if this author batch is deliberately rerun.
    for slot,choices in old.get('slots',{}).items():
        if slot=='body':continue
        for option,spec in choices.items():
            if option not in catalog['slots'].get(slot,{}):catalog['slots'].setdefault(slot,{})[option]=spec
    bench=copy.deepcopy(read(DATA/'warhammer-gunsmith.json'))
    bench['weapon']=ID
    for column in bench['columns']:
        column['options']=[]  # The donor's exclusive meteor head is not a common accessory.
        if column['key']=='rune':column['default']='无附加符文';column['description']='保留原生刻纹，可在金属长柄附加通用符文。'
        if column['key']=='head_mount':column['description']='保留原装符文锤座；通用锤座按本锤真实侧接面与锤颈接口装配。'
        if column['key']=='grip':column['description']='沿用现有双手接触位置，替换下段包覆并保留两端安装截面。'
    passive=P.parent/'PassiveV1'
    if (passive/'import_receipt.json').exists() and read(passive/'import_receipt.json').get('complete'):
        import runpy
        runpy.run_path(str(passive/'publish_recipe.py'))['apply'](catalog,bench)
    write(DATA/'runebound-warhammer-modules.json',catalog)
    write(DATA/'runebound-warhammer-gunsmith.json',bench)
    (P/'catalog_base.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    (P/'workbench.json').write_text(json.dumps(bench,ensure_ascii=False,indent=2),encoding='utf-8')
    target=DATA/'AttachmentIcons20260913'
    for suffix in ('category_rune','rune_false'):
        shutil.copy2(target/(suffix+'.png'),target/(ID+'_'+suffix+'.png'))
    print('RUNEBOUND_HAMMER_MODULE_CATALOGS_PUBLISHED')

if __name__=='__main__':publish()
