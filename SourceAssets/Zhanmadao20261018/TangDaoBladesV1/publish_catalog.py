"""Publish only the two saved TangDao blades, preserving other weapon choices."""
import copy,json,shutil,runpy
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
D='/Game/Weapons/Zhanmadao20261018/TangDaoBladesV1'
OPTIONS=('yanling_edge','tengyun_dragon')

def publish():
    receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
    if not receipt.get('assets_saved'):raise RuntimeError('Save the fitted blades and their standard icons before publishing')
    def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
    target=read('zhanmadao-modules.json');source=read('tang-dao-modules.json');guns=read('melee-gunsmith.json')
    exports=json.loads((P/'blade_exports.json').read_text(encoding='utf-8'))
    matrix=[]
    for export in exports['options']:
        option=export['id'];part=copy.deepcopy(source['slots']['blade_1'][option])
        name=export['mesh_name'];part.update(mesh=D+'/Meshes/'+name+'.'+name,
            interface=target['interface'],location_cm=[0,0,0],rotation_deg=[0,0,0],scale=[1,1,1])
        for key in ['trace_base_cm','trace_tip_cm','rune_dimensions_cm']:part[key]=export[key]
        target['slots']['blade_1'][option]=part
        entry=next(o for c in guns['columns'] if c['key']=='blade_1' for o in c['options'] if o['id']==option)
        if 'ue_zhanmadao' not in entry['weapons']:entry['weapons'].append('ue_zhanmadao')
        entry['description']=entry['description'].removeprefix('唐刀专属。')
        matrix.append({'id':option,'name':entry['name'],'mesh':part['mesh'],
            'combo_third_attack':part['combo_third_attack'],'stats':copy.deepcopy(entry['stats']),
            'icon':'/Game/ColdSteelData/AttachmentIcons20260913/ue_zhanmadao_blade_1_'+option,
            'icon_master':'ue_tang_dao_blade_1_'+option+'.png','materials':part['materials']})
    target['tangdao_blade_revision']='TangDaoBladesV1'
    extension=P.parent/'RuneSurfaceV1/catalog_extension.py'
    if extension.exists():
        target=runpy.run_path(str(extension))['extend'](target)
        for entry in matrix:entry['materials']=copy.deepcopy(target['slots']['blade_1'][entry['id']]['materials'])
    backup=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
    for name,value in [('zhanmadao-modules.json',target),('melee-gunsmith.json',guns)]:
        file=DATA/name;shutil.copy2(file,backup/name)
        tmp=file.with_suffix('.zhan-blades.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(file)
    result={'weapon':'ue_zhanmadao','slot':'blade_1','options':matrix,'catalog_saved':True,
        'attack_reach_unchanged_cm':225,'factory_rigid_length_unchanged_cm':160.13139188289642,
        'game_tested':False,'backup':str(backup)}
    (P/'catalog_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
if __name__=='__main__':publish()
