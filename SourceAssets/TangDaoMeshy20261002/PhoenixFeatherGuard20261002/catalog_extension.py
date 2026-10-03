"""Add a distinct phoenix guard; merge only this option and its material binding."""
import copy,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
def installed():
    path=P/'import_receipt.json'
    return path.exists() and json.loads(path.read_text(encoding='utf-8')).get('complete',False)
def manifest():return json.loads((P/'guard_manifest.json').read_text(encoding='utf-8'))
def add_module(catalog):
    m=manifest();row={k:copy.deepcopy(m[k]) for k in ['mesh','interface','location_cm','rotation_deg','scale','materials']}
    row['appearance']='凤羽层叠外缘、双面凤首与羽脊实体浮雕、卷云及羽隙贯通镂空，两处红石嵌饰与雕纹止滑环。'
    catalog['slots'].setdefault('guard',{})[m['id']]=row
    catalog['phoenix_feather_guard_revision']='TangDaoPhoenixFeatherGuard20261002'
def add_bindings(bindings):
    m=manifest();bindings['slots'].setdefault('guard',{})[m['id']]=copy.deepcopy(m['materials'])
def add_option(gunsmith):
    m=manifest();column=next(c for c in gunsmith['columns'] if c['key']=='guard')
    row={'id':m['id'],'name':m['name'],'weapons':['ue_tang_dao'],
         'description':'唐刀专属护手。层叠凤羽与凤首浮雕形成不对称外缘，卷云羽隙贯通镂空，暖鎏金凸纹配暗铜凹底和红石嵌饰。',
         'effects':[{'text':'层叠凤羽护缘 · 双面凤纹实体浮雕','benefit':0},{'text':'卷云羽隙镂空 · 红石嵌饰与止滑环','benefit':0}],
         'stats':{}}
    for i,old in enumerate(column['options']):
        if old['id']==m['id']:
            row['stats']=copy.deepcopy(old.get('stats',{}));column['options'][i]=row;break
    else:column['options'].append(row)
def install():
    if not installed():raise RuntimeError('Save the actual phoenix guard assets before publishing option')
    paths=[(DATA/'tang-dao-modules.json',add_module),(DATA/'melee-gunsmith.json',add_option),(P.parent/'SurfaceV2/bindings.json',add_bindings)]
    for path,merge in paths:
        value=json.loads(path.read_text(encoding='utf-8-sig'));merge(value)
        backup=P/'Before'/path.name
        if not backup.exists():shutil.copy2(path,backup)
        temp=path.with_suffix(path.suffix+'.phoenixguard.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
    (P/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_tang_dao','slot':'guard','option':'phoenix_feather','stats':{},
        'runtime_tested':False,'catalogs':[str(x) for x,_ in paths]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PHOENIX_FEATHER_GUARD_OPTION_INSTALLED',flush=True)
if __name__=='__main__':install()
