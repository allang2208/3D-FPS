"""Merge one TangDao-specific pommel without altering shared pommel choices."""
import copy,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
def installed():
    path=P/'import_receipt.json'
    return path.exists() and json.loads(path.read_text(encoding='utf-8')).get('complete',False)
def manifest():return json.loads((P/'pommel_manifest.json').read_text(encoding='utf-8'))
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
        'effects':[{'text':s,'benefit':0} for s in m.get('effects_text',['张口虎首 · 深腔与独立獠牙','卷云鬃纹浮雕 · 红石虎目和冠带'])],
        'stats':{}}
    for i,old in enumerate(column['options']):
        if old['id']==m['id']:
            row['stats']=copy.deepcopy(old.get('stats',{}));column['options'][i]=row;break
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
        'stats':{},'shared_options_preserved':True,'long_grip_follow':'existing pommel_offset_cm',
        'runtime_tested':False,'catalogs':[str(x) for x,_ in paths]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TIGER_POMMEL_OPTION_INSTALLED',flush=True)
if __name__=='__main__':install()
