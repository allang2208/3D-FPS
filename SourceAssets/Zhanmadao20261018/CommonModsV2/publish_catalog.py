"""Merge the twenty established common choices and fitted model entries only."""
import copy,json,shutil,runpy
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData';ID='ue_zhanmadao'
D='/Game/Weapons/Zhanmadao20261018/CommonModsV2'
COMMON={
 'blade_1':['extended_edge','heavy_spine','feather_edge'],
 'blade_2':['strength_rune','haste_rune','resonance_rune','erosion_rune','conduction_rune'],
 'guard':['bastion_guard','riposte_guard','light_guard'],
 'grip':['shock_wrap','swift_grip','long_twohand','iron_spine_power_grip','lockweave_guard_grip'],
 'pommel':['pommel_hardened','pommel_runic','ballast_hardened','ballast_magic_orb']}
def publish():
    receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
    if not receipt.get('assets_saved'):raise RuntimeError('Save all fitted modules and icons before publishing')
    variants=json.loads((P/'variant_exports.json').read_text(encoding='utf-8'))
    grips=json.loads((P/'grip_exports.json').read_text(encoding='utf-8'))
    BACK=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S');BACK.mkdir(parents=True,exist_ok=True)
    def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
    def write(name,value):
        path=DATA/name;shutil.copy2(path,BACK/name)
        tmp=path.with_suffix('.zhan-common.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
    def mesh(name):return D+'/Meshes/'+name+'.'+name
    catalog=read('zhanmadao-modules.json')
    for row in variants['options']:
        part=copy.deepcopy(catalog['slots'][row['slot']]['factory'])
        part.update(mesh=mesh(row['mesh']),appearance=row['appearance'])
        if row['slot']=='blade_1':part['rune_dimensions_cm']=row['rune_dimensions_cm']
        catalog['slots'][row['slot']][row['option']]=part
    labels={'shock_wrap':'交错吸震缠带 · 斩马刀原装上下接口',
            'swift_grip':'收束握区与浅导向细脊 · 斩马刀原装接口',
            'long_twohand':'加长双手握区 · 柄尾与共用配重联动',
            'iron_spine_power_grip':'贴平钢脊与三段皮革握区 · 原装接口',
            'lockweave_guard_grip':'交错锁纹织带与浅菱格 · 原装接口'}
    for row in grips['options']:
        part=copy.deepcopy(catalog['slots']['grip']['factory'])
        part.update(mesh=mesh(row['mesh']),pommel_offset_cm=row['pommel_offset_cm'],appearance=labels[row['option']])
        if row['animation_folder']:part['animation_folder']=row['animation_folder']
        catalog['slots']['grip'][row['option']]=part
    profile={'library':'shared-sword-pommels.json','finish':'silver','interfaces':{}}
    for row in variants['adapters']:
        location=list(row['mount_cm']);location[2]-=row['depth_cm']
        profile['interfaces'][row['interface']]={'location_cm':location,'rotation_deg':[0,0,0],'scale':[row['scale']]*3,
            'adapter':{'mesh':mesh(row['mesh']),'location_cm':row['mount_cm'],'interface':'zhanmadao_to_'+row['interface']}}
    catalog['pommel_profile']=profile;catalog['common_modification_revision']='CommonModsV2'
    guns=read('melee-gunsmith.json');matrix=[];shared=read('shared-sword-pommels.json')
    for column in guns['columns']:
        slot=column['key']
        for option in column['options']:
            if option['id'] not in COMMON.get(slot,[]):continue
            if option.get('weapons') and ID not in option['weapons']:option['weapons'].append(ID)
            icon=DATA/'AttachmentIcons20260913'/(slot+'_'+option['id']+'.png')
            if not icon.exists():raise RuntimeError('Common icon source missing: '+str(icon))
            model=catalog['slots'].get(slot,{}).get(option['id'],{}).get('mesh')
            if slot=='pommel':model=shared['options'][option['id']]['mesh']
            matrix.append({'slot':slot,'id':option['id'],'name':option['name'],'model':model,
                'material_overlay':slot=='blade_2','icon':str(icon),'icon_policy':'existing shared master',
                'stats':'unchanged existing catalog values'})
    extension=P.parent/'RuneSurfaceV1/catalog_extension.py'
    if extension.exists():catalog=runpy.run_path(str(extension))['extend'](catalog)
    write('zhanmadao-modules.json',catalog);write('melee-gunsmith.json',guns)
    coverage={'weapon':ID,'common_count':len(matrix),'common_options':matrix,
        'factory_icons':json.loads((P/'icon_deployments.json').read_text(encoding='utf-8')),
        'rune_category_icon':str(DATA/'AttachmentIcons20260913/category_blade_2.png'),
        'backup':str(BACK),'native_code_changed':False,'game_tested':False}
    (P/'integration_matrix.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return coverage
if __name__=='__main__':publish()
