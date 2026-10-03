"""Register only the saved TangDao Tengyun blade; keep existing parts and stats."""
import copy, json, shutil
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT/'Content/ColdSteelData'
def installed():
    file = P/'import_receipt.json'
    return file.exists() and json.loads(file.read_text(encoding='utf-8')).get('complete',False)
def manifest():
    return json.loads((P/'blade_manifest.json').read_text(encoding='utf-8'))
def add_module(catalog):
    m = manifest()
    keys = ['mesh','interface','location_cm','trace_base_cm','trace_tip_cm','rune_dimensions_cm','materials']
    row = {key:copy.deepcopy(m[key]) for key in keys}
    row['appearance'] = '弧形轻量刀尖、龙脊长导槽与鎏金游龙浮雕，流云暗纹融合水波锻钢纹。'
    catalog['slots']['blade_1'][m['id']] = row
    catalog['tengyun_surface_revision'] = 'TangDaoTengyunBlade20261002'
def add_bindings(bindings):
    m = manifest()
    bindings['slots'].setdefault('blade_1',{})[m['id']] = copy.deepcopy(m['materials'])
def add_option(gunsmith):
    m = manifest()
    column = next(c for c in gunsmith['columns'] if c['key']=='blade_1')
    option = {'id':m['id'],'name':m['name'],'weapons':['ue_tang_dao'],
        'description':'唐刀专属刀身。弧形刀尖接修长龙脊导槽，鎏金游龙沿刃面腾行，流云暗纹与层叠水波锻纹交织。',
        'effects':[{'text':'弧形刀尖 · 龙脊长导槽','benefit':0},{'text':'鎏金游龙浮雕 · 流云水波锻纹','benefit':0}],
        'stats':{}}
    for index, old in enumerate(column['options']):
        if old['id']==m['id']:
            column['options'][index]=option
            break
    else: column['options'].append(option)
def install():
    if not installed(): raise RuntimeError('Save the Tengyun assets before installing its option')
    changes = [('tang-dao-modules.json',DATA/'tang-dao-modules.json',add_module),
        ('melee-gunsmith.json',DATA/'melee-gunsmith.json',add_option),
        ('bindings.json',P.parent/'SurfaceV2/bindings.json',add_bindings)]
    for name,path,merge in changes:
        value=json.loads(path.read_text(encoding='utf-8-sig'))
        merge(value)
        backup=P/'Before'/name
        if not backup.exists(): shutil.copy2(path,backup)
        temporary=path.with_suffix(path.suffix+'.tengyun.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temporary.replace(path)
    (P/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_tang_dao','slot':'blade_1','option':'tengyun_dragon',
        'saved_assets_required':True,'gameplay_stats_changed':False,'holding_interface_changed':False,
        'runtime_tested':False,'catalogs':[str(path) for _,path,_ in changes]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TENGYUN_BLADE_OPTION_INSTALLED',flush=True)
if __name__=='__main__': install()
