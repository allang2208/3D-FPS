"""Install TangDao's saved cloud rune and its three distinct steel surfaces."""
from pathlib import Path
import json, shutil

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT/'Content/ColdSteelData'
REVISION = 'TangDaoAuspiciousCloudRune20261002'
ID = 'auspicious_cloud_rune'
UE_ROOT = '/Game/Weapons/TangDao20261002/CloudRune20261002'
SOURCE_PATHS = [
    '/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoBladeRuneSurface',
    '/Game/Weapons/TangDao20261002/YanlingBlade20261002/Materials/M_TangDaoBladeRuneSurface_Yanling',
    '/Game/Weapons/TangDao20261002/TengyunBlade20261002/Materials/M_TangDaoBladeRuneSurface_Tengyun']
MATERIAL_NAMES = ['M_TangDaoBladeRuneSurface_CloudBase',
                  'M_TangDaoBladeRuneSurface_CloudYanling',
                  'M_TangDaoBladeRuneSurface_CloudTengyun']

def object_path(path):
    return path if '.' in path else path+'.'+path.rsplit('/',1)[-1]

MATERIALS = {object_path(source):object_path(UE_ROOT+'/Materials/'+name)
             for source,name in zip(SOURCE_PATHS,MATERIAL_NAMES)}

def installed():
    file=P/'import_receipt.json'
    return file.exists() and json.loads(file.read_text(encoding='utf-8')).get('complete',False)

def add_module(catalog):
    for row in catalog['slots']['blade_1'].values():
        row['materials']={key:MATERIALS.get(object_path(value),value)
                          for key,value in row.get('materials',{}).items()}
    catalog['cloud_rune_revision']=REVISION

def add_bindings(bindings):
    for choice,materials in bindings['slots']['blade_1'].items():
        bindings['slots']['blade_1'][choice]={key:MATERIALS.get(object_path(value),value)
                                           for key,value in materials.items()}
    bindings['cloud_rune_revision']=REVISION

def add_option(gunsmith):
    column=next(c for c in gunsmith['columns'] if c['key']=='blade_2')
    option={'id':ID,'name':'祥云符文','weapons':['ue_tang_dao'],
        'description':'唐刀专属。卷云主印向刀尖收成流云，淡金云纹间流转玉青微光。云气托刃，出手更快、更省耐力，击杀时回收体力，削弱攻击造成的韧性伤害。',
        'appearance':'卷云主印 · 淡金云纹 · 玉青流光',
        'effects':[{'text':'攻击速度 +10%','benefit':1},
                   {'text':'攻击耐力消耗 -15%','benefit':1},
                   {'text':'击杀任何目标后，恢复最大体力值的15%','benefit':1},
                   {'text':'攻击韧性伤害 -10%','benefit':-1}],
        'stats':{'attack_speed_mult':1.10,'stamina_mult':.85,'toughness_damage_mult':.90,'kill_stamina_max_ratio':.15}}
    for i,old in enumerate(column['options']):
        if old['id']==ID:
            column['options'][i]=option
            break
    else:column['options'].append(option)

def write(path,value):
    backup=P/'Before'/path.relative_to(ROOT)
    backup.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and not backup.exists():shutil.copy2(path,backup)
    temp=path.with_suffix(path.suffix+'.cloudrune.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)

def install():
    if not installed():raise RuntimeError('Save the cloud rune assets before registering its option')
    changes=[(DATA/'tang-dao-modules.json',add_module),
             (DATA/'melee-gunsmith.json',add_option),
             (P.parent/'SurfaceV2/bindings.json',add_bindings)]
    for path,merge in changes:
        value=json.loads(path.read_text(encoding='utf-8-sig'))
        merge(value)
        write(path,value)
    mapping_file=DATA/'whirlwind-temporal-materials.json'
    mapping=json.loads(mapping_file.read_text(encoding='utf-8-sig'))
    for path in MATERIALS.values():
        mapping[path]=object_path(path.split('.')[0]+'_Whirlwind')
    write(mapping_file,mapping)
    (P/'catalog_receipt.json').write_text(json.dumps({
        'weapon':'ue_tang_dao','slot':'blade_2','option':ID,
        'saved_assets_required':True,'effects':{'attack_speed_mult':1.10,'stamina_mult':.85,'toughness_damage_mult':.90,'kill_stamina_max_ratio':.15},
        'material_bindings':MATERIALS,'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TANGDAO_CLOUD_RUNE_OPTION_INSTALLED',flush=True)

if __name__=='__main__':install()
