"""Merge one TangDao-specific pommel without altering shared pommel choices."""
import copy,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
TIGER_ROAR_STATS={'quick_combat_tiger_roar_toughness_bonus':0.25,'quick_combat_tiger_roar_seconds':6}
TIGER_ROAR_EFFECTS=[
    {'text':'快速近战命中敌人后施加虎啸，持续6秒；重复命中刷新，不叠加','benefit':1},
    {'text':'虎啸：冲击、利器、钝器的韧性抵抗归零，受到的韧性伤害提高25%','benefit':1}]
def active_root():
    marker=P/'active_revision.json'
    if marker.exists():
        return P/json.loads(marker.read_text(encoding='utf-8'))['source_revision']
    return P

def installed():
    path=active_root()/'import_receipt.json'
    return path.exists() and json.loads(path.read_text(encoding='utf-8')).get('complete',False)
def manifest():return json.loads((active_root()/'pommel_manifest.json').read_text(encoding='utf-8'))
def add_module(catalog):
    m=manifest()
    row={k:copy.deepcopy(m[k]) for k in ['mesh','interface','location_cm','rotation_deg','scale','materials']}
    row['appearance']=m.get('appearance','圆厚虎首、卷云鬃纹实体浮雕与深口腔，独立獠牙、红石虎目及冠饰宝带。')
    catalog['slots'].setdefault('pommel',{})[m['id']]=row
    catalog['tiger_pommel_revision']=m.get('revision','TangDaoTigerPommel20261002')
def add_bindings(bindings):
    m=manifest();bindings['slots'].setdefault('pommel',{})[m['id']]=copy.deepcopy(m['materials'])
def add_option(gunsmith):
    m=manifest();column=next(c for c in gunsmith['columns'] if c['key']=='pommel')
    row={'id':m['id'],'name':m['name'],'weapons':['ue_tang_dao'],
        'description':'唐刀专属柄尾。'+m.get('appearance','虎首浮雕衔接云环尾扣，张口獠牙配暗铜凹底、暖鎏金凸纹与红石嵌饰。'),
        'effects':copy.deepcopy(TIGER_ROAR_EFFECTS),
        'stats':copy.deepcopy(TIGER_ROAR_STATS)}
    for i,old in enumerate(column['options']):
        if old['id']==m['id']:
            row['stats']={**copy.deepcopy(old.get('stats',{})),**TIGER_ROAR_STATS};column['options'][i]=row;break
    else:column['options'].append(row)
def install():
    if not installed():raise RuntimeError('Save the actual pommel assets before registering its option')
    m=manifest();revision_dir=m.get('source_revision','ReferenceV2' if m.get('revision')=='TangDaoTigerPommelReferenceV2_20261002' else '')
    backup_dir=P/revision_dir/'Before';backup_dir.mkdir(parents=True,exist_ok=True)
    paths=[(DATA/'tang-dao-modules.json',add_module),(DATA/'melee-gunsmith.json',add_option),(P.parent/'SurfaceV2/bindings.json',add_bindings)]
    for path,merge in paths:
        value=json.loads(path.read_text(encoding='utf-8-sig'));merge(value)
        backup=backup_dir/path.name
        if not backup.exists():shutil.copy2(path,backup)
        temp=path.with_suffix(path.suffix+'.tigerpommel.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
    (P/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_tang_dao','slot':'pommel','option':'tiger_mountain',
        'stats':TIGER_ROAR_STATS,'shared_options_preserved':True,'long_grip_follow':'existing pommel_offset_cm',
        'runtime_tested':False,'catalogs':[str(x) for x,_ in paths]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TIGER_POMMEL_OPTION_INSTALLED',flush=True)
if __name__=='__main__':install()
