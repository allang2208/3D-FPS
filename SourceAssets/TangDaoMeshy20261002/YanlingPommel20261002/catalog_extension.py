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
    row['appearance']=m.get('appearance','饱满燕翎十折面锤头、短圆角八角环与贴面鎏金盾框；龙云浅浮雕嵌在后部甲片，前部保留裸黑钢尖锋。')
    catalog['slots'].setdefault('pommel',{})[m['id']]=row
    catalog['yanling_pommel_revision']=m.get('revision','TangDaoYanlingPommel20261002')
def add_bindings(bindings):
    m=manifest();bindings['slots'].setdefault('pommel',{})[m['id']]=copy.deepcopy(m['materials'])
def add_option(gunsmith):
    m=manifest();column=next(c for c in gunsmith['columns'] if c['key']=='pommel')
    row={'id':m['id'],'name':m['name'],'weapons':['ue_tang_dao'],
        'description':'唐刀专属柄尾。'+m.get('appearance','短圆角八角环衔接饱满的燕翎折面锤头，贴面鎏金盾框环绕龙云甲片，黑钢尖锋延续破锋轮廓。'),
        'effects':[{'text':s,'benefit':0} for s in m.get('effects_text',['燕翎十折面锤头 · 短圆角八角环','贴面鎏金盾框 · 龙云甲片浮雕'])],
        'stats':{}}
    for i,old in enumerate(column['options']):
        if old['id']==m['id']:
            row['stats']=copy.deepcopy(old.get('stats',{}));column['options'][i]=row;break
    else:column['options'].append(row)
def install():
    if not installed():raise RuntimeError('Save the actual pommel assets before registering its option')
    m=manifest();revision_dir=m.get('source_revision','ReferenceV2' if m.get('revision')=='TangDaoYanlingPommelReferenceV2_20261002' else '')
    backup_dir=P/revision_dir/'Before';backup_dir.mkdir(parents=True,exist_ok=True)
    paths=[(DATA/'tang-dao-modules.json',add_module),(DATA/'melee-gunsmith.json',add_option),(P.parent/'SurfaceV2/bindings.json',add_bindings)]
    for path,merge in paths:
        value=json.loads(path.read_text(encoding='utf-8-sig'));merge(value)
        backup=backup_dir/path.name
        if not backup.exists():shutil.copy2(path,backup)
        temp=path.with_suffix(path.suffix+'.yanlingpommel.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
    (P/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_tang_dao','slot':'pommel','option':'yanling_breaker',
        'stats':{},'shared_options_preserved':True,'long_grip_follow':'existing pommel_offset_cm',
        'runtime_tested':False,'catalogs':[str(x) for x,_ in paths]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('YANLING_POMMEL_OPTION_INSTALLED',flush=True)
if __name__=='__main__':install()
