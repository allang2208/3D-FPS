"""Register one TangDao-exclusive guard, preserving other choices and rune bindings."""
import copy,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'

def installed():
    path=P/'import_receipt.json'
    return path.exists() and json.loads(path.read_text(encoding='utf-8')).get('complete',False)
def manifest():return json.loads((P/'guard_manifest.json').read_text(encoding='utf-8'))

def add_module(catalog):
    m=manifest();row={k:copy.deepcopy(m[k]) for k in ['mesh','interface','location_cm','rotation_deg','scale','materials']}
    row['appearance']='四瓣璇云层叠轮廓，双面龙云实体浮雕、贯通云纹镂空与雕纹止滑环。'
    catalog['slots'].setdefault('guard',{})[m['id']]=row
    catalog['xuan_cloud_guard_revision']='TangDaoXuanCloudGuard20261002'

def add_bindings(bindings):
    m=manifest();bindings['slots'].setdefault('guard',{})[m['id']]=copy.deepcopy(m['materials'])

def add_option(gunsmith):
    m=manifest();column=next(c for c in gunsmith['columns'] if c['key']=='guard')
    row={'id':m['id'],'name':m['name'],'weapons':['ue_tang_dao'],
        'description':'唐刀专属护手。璇云四瓣层叠边框环绕龙云浮雕，暗铜凹底映衬鎏金凸纹，贯通云孔与雕纹止滑环延续唐风。',
        'effects':[{'text':'璇云层叠边框 · 双面龙云浮雕','benefit':0},{'text':'云纹贯通镂空 · 雕纹止滑环','benefit':0}],
        'stats':{}}
    for i,old in enumerate(column['options']):
        if old['id']==m['id']:column['options'][i]=row;break
    else:column['options'].append(row)

def install():
    if not installed():raise RuntimeError('Save the actual guard assets before registering the option')
    paths=[(DATA/'tang-dao-modules.json',add_module),(DATA/'melee-gunsmith.json',add_option),(P.parent/'SurfaceV2/bindings.json',add_bindings)]
    for path,merge in paths:
        value=json.loads(path.read_text(encoding='utf-8-sig'));merge(value)
        backup=P/'Before'/path.name
        if not backup.exists():shutil.copy2(path,backup)
        temp=path.with_suffix(path.suffix+'.xuancloudguard.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
    (P/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_tang_dao','slot':'guard','option':'xuan_cloud_dragon','stats':{},
        'runtime_tested':False,'catalogs':[str(x) for x,_ in paths]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('XUAN_CLOUD_GUARD_OPTION_INSTALLED',flush=True)
if __name__=='__main__':install()
