"""Publish this new hammer only after its own new asset packages have been saved."""
import copy,json,os
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
ID='ue_thunder_god_hammer';D='/Game/Weapons/ThunderGodHammer20261028'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write_new(path,value):
    content=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if path.exists():
        if read(path)==value:return
        raise RuntimeError('Preserve changed destination: '+str(path))
    path.write_text(content,encoding='utf-8')
def append(filename,value):
    path=DATA/filename;before=path.read_bytes();text=before.decode('utf-8-sig');data=json.loads(text)
    if ID in data:
        if data[ID]==value:return
        raise RuntimeError('Existing item definition differs: '+filename)
    backup=P/'Before'/filename;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    end=text.rfind('}');entry=json.dumps(ID)+': '+json.dumps(value,ensure_ascii=False,indent=2)
    content=text[:end].rstrip()+',\n  '+entry.replace('\n','\n  ')+'\n'+text[end:]
    tmp=path.with_name(path.name+'.thunder-god-hammer.tmp');tmp.write_text(content,encoding='utf-8')
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog write: '+filename)
    os.replace(tmp,path)
def main():
    if not read(P/'import_receipt.json').get('complete') or not read(P/'ModulesV1/import_receipt.json').get('complete'):
        raise RuntimeError('Save this hammer and its modules before publication')
    item=copy.deepcopy(read(DATA/'items.json')['ue_steel_warhammer'])
    mesh=D+'/SM_ThunderGodHammer.SM_ThunderGodHammer'
    item.update(id=ID,name='雷神之锤',
        desc='北境匠人以雷神传说为名铸成的长柄战锤，银色编纹环抱锤首的三角交结印。木柄与皮革握区适合双手分握，横挥借长柄带起锤首，蓄势下砸则将重量集中于落点；需为沉重的收势留出余地。',
        ue_icon='Icons/'+ID+'.png',icon_fallback='雷神之锤',tool_mesh=mesh,world_mesh=mesh,
        modular_melee_catalog='thunder-god-hammer-modules.json')
    item.pop('rarity',None);item.pop('grade',None)
    factory=read(P/'ModulesV1/exports.json')['parts'];fitted=read(P/'ModulesV1/adapted_exports.json')['parts']
    common=read(DATA/'warhammer-modules.json')
    catalog={'version':1,'weapon':ID,'interface':'thunder_god_hammer_modular_v1',
      'arms_mesh':item['tool_viewmodel'],'root_slot':'head_mount','module_slots':[r['slot'] for r in factory],
      'drive_bone':'WPN_root','bone_mount':copy.deepcopy(common['bone_mount']),'slots':{}}
    libraries={'hammer_heads':'common-hammer-heads.json','head_mount':'common-hammer-seats.json',
      'grip':'common-hammer-grips.json','pommel':'common-hammer-pommels.json'}
    appearances={slot:{o['id']:o['appearance'] for o in read(DATA/file)['options']} for slot,file in libraries.items()}
    for row in factory+fitted:
        slot=row['slot'];option=row['id'];package=D+'/ModulesV1/'+row['mesh']
        spec={'mesh':package+'.'+row['mesh'],'location_cm':row['location_cm'],
          'appearance':('原装'+row['name']) if option=='factory' else appearances[slot][option]}
        if option!='factory':spec.update(interface=catalog['interface'],shared_option_library=libraries[slot],
          model_revision='ThunderGodHostSectionFitV1',source_mesh=row['source_mesh'])
        catalog['slots'].setdefault(slot,{})[option]=spec
    catalog['slots']['rune']=copy.deepcopy(common['slots']['rune'])
    catalog['slots']['rune']['factory']['appearance']='保留原生雷纹 · 不附加符文'
    bench=copy.deepcopy(read(DATA/'warhammer-gunsmith.json'));bench['weapon']=ID
    desc={
      'hammer_heads':'两端层叠锤面成对装配，保留银色编纹与蓝色原生刻纹。',
      'head_mount':'中央圆形雷纹徽记连接双侧锤头，北欧编织纹沿金属边框收束。',
      'rune':'保留原生雷纹，可在长柄上附加通用符文。',
      'grip':'连续皮革缠裹保留双手接触范围，两端以窄金属环收口。',
      'pommel':'刻有细小雷纹的多面金属配重，与握区下端连续衔接。'}
    for col in bench['columns']:
        col['options']=[];col['description']=desc[col['key']]
        if col['key']=='rune':col['default']='无附加符文'
    for filename,value in [('thunder-god-hammer-modules.json',catalog),('thunder-god-hammer-gunsmith.json',bench)]:
        write_new(DATA/filename,value)
    write_new(P/'ModulesV1/catalog_base.json',catalog);write_new(P/'ModulesV1/workbench.json',bench)
    append('items.json',item)
    formula=copy.deepcopy(read(DATA/'combat-weapon-formulas.json')['ue_steel_warhammer'])
    formula['source']='THUNDER_GOD_HAMMER_STR_CON_20261028'
    append('combat-weapon-formulas.json',formula)
    write_new(P/'item_definition.json',item)
    config=ROOT/'Config/DefaultGame.ini';before=config.read_bytes();text=before.decode('utf-8-sig')
    line='+DirectoriesToAlwaysCook=(Path="'+D+'")'
    if line not in text:
        anchor='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/SteelWarhammer20261014")'
        if anchor not in text:raise RuntimeError('Packaging section anchor changed')
        backup=P/'Before/DefaultGame.ini'
        if not backup.exists():backup.write_bytes(before)
        content=text.replace(anchor,anchor+'\n'+line,1)
        if config.read_bytes()!=before:raise RuntimeError('Concurrent packaging config write')
        config.write_text(content,encoding='utf-8',newline='\n')
    (P/'publication_receipt.json').write_text(json.dumps({'complete':True,'definition':ID,'factory_modules':len(factory),
      'fitted_common_modules':len(fitted),'shared_runes':5,'animation_assets_copied':0,
      'native_elemental_gameplay_added':False,'source_material_emission':'GLB has no emissive channel; preserve native PBR',
      'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
    print('THUNDER_GOD_HAMMER_PUBLISHED')
if __name__=='__main__':main()
