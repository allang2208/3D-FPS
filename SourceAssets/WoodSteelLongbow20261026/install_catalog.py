"""Install this weapon's records into the latest shared catalogs after asset saving."""
from pathlib import Path
import copy, json, datetime, os
P=Path(__file__).parent
project=Path('D:/FPS3D/FPSGAME');data=project/'Content/ColdSteelData'
for receipt in ['import-receipt.json','icon-import-receipt.json']:
    if not json.loads((P/receipt).read_text()).get('complete'):
        raise RuntimeError('Finish asset publishing before catalog activation: '+receipt)
before=P/'Before'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');before.mkdir(parents=True)
manifest=json.loads((P/'authoring.json').read_text())
saved=[]
def vec(v):return ','.join(f'{n:.5f}'.rstrip('0').rstrip('.') if n else '0' for n in v)
def asset(name):return '/Game/Weapons/WoodSteelLongbow20261026/'+name+'.'+name
def edit_json(name,mutate):
    path=data/(name+'.json');raw=path.read_bytes();d=json.loads(raw.decode('utf-8-sig'))
    mutate(d)
    output=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if output==raw:return
    if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during edit; rerun safely: '+name)
    (before/path.name).write_bytes(raw)
    temp=path.with_name(path.name+'.woodsteel.tmp');temp.write_bytes(output);os.replace(temp,path)
    saved.append(str(path))
def bow(d):
    b=copy.deepcopy(d['bow_dark'])
    b.update(id='bow_woodsteel',name='高地长弓',ue_icon='Icons/bow_woodsteel.png',price=1280,
        desc='高地哨卫以层压长木为弓胎，用暗色钢片包护弓根与叶形弓梢。旧革缠带与侧置箭台保留了山地猎人的习惯，修长弓臂为越过谷地的远射蓄力。使用者须先站稳脚跟，再以沉着的拉放节奏寻找远处的破绽。',
        range_cm=4800,critDamageBonus=0,bow_traits_revision=2,
        bow_part_riser_mesh=asset('SK_WoodSteelLongbow_Original'),bow_part_riser_material='',bow_part_riser_scale=1,
        bow_part_grip_mesh=asset('SM_WoodSteelLongbow_Grip'),bow_part_grip_material='',bow_part_grip_scale=1,
        bow_part_arrow_rest_mesh=asset('SM_WoodSteelLongbow_Rest'),bow_part_arrow_rest_material='',bow_part_arrow_rest_scale=1,
        bow_part_sight_mesh='',bow_part_sight_material='',bow_part_sight_rods=0,bow_ads_sight_cm='',
        bow_ads_rest_cm='63,10,-12',bow_scope_magnification=1,bow_scale=1,
        bow_length_cm=manifest['bow_length_cm'],bow_depth_cm=manifest['bow_depth_cm'],
        bow_fit_shared_contact=1,bow_reference_brace_cm='-24.081,0.123,1.5',bow_reference_draw_cm='-52.581,0.123,1.5',
        bow_presentation_revision=36)
    for key in ['nock_upper_cm','nock_lower_cm','brace_nock_cm','draw_anchor_cm','arrow_rest_cm']:b[key]=vec(manifest[key])
    d['bow_woodsteel']=b
edit_json('bows',bow)
def gunsmith(d):
    # The hunter has a factory sight to remove; the Highland factory is already bare.
    sight=next(c for c in d['columns'] if c['key']=='sight')
    next(o for o in sight['options'] if o['id']=='no_sight')['weapons']=['bow_dark']
    source=next(x for x in d['weapons'] if x['id']=='bow_dark')
    w={'id':'bow_woodsteel','traits':copy.deepcopy(source.get('traits',[])),
       'shared_icon_weapon':'bow_dark','part_overrides':{},
       'category_icon_sources':{'riser':'bow_woodsteel_riser_false','grip':'bow_woodsteel_grip_false',
          'arrow_rest':'bow_woodsteel_arrow_rest_false','string':'bow_dark_category_string','sight':'bow_dark_category_sight'},
       'factory_icon_sources':{'string':'bow_dark_string_false','sight':'bow_dark_sight_no_sight'}}
    w['traits']=[{'icon':'special','text':'有效射程+50%'},
                 {'icon':'mechanic','text':'无声射击：拉弓、放箭与箭矢命中不会通过声音引起怪物警觉'}]
    parts=w['part_overrides']
    def part(slot,key,mesh,name=None,description=None,appearance=None,extra=None):
        visual={'bow_part_'+slot+'_mesh':asset(mesh) if mesh else '',
                'bow_part_'+slot+'_material':'','bow_part_'+slot+'_scale':1}
        if slot!='riser':visual['bow_part_'+slot+'_rods']=0
        if extra:visual.update(extra)
        value={'visual':visual}
        for field,text in [('name',name),('description',description),('appearance',appearance)]:
            if text is not None:value[field]=text
        parts.setdefault(slot,{})[key]=value
    part('riser','false','SK_WoodSteelLongbow_Original','原装木钢弓体','原弓的长木弓胎与金属护片组合，保留叶形弓梢。','修长木纹弓臂、暗金属护片与叶形弓梢。')
    for key,suffix,appearance in [('strong_draw','Original','保留原装木钢弓体外形；本项调校拉力。'),
          ('swift_limb','Swift','收薄木钢弓臂，保留原有金属护片轮廓。'),
          ('heavy_limb','Heavy','加厚木钢弓臂，保留叶形弓梢。'),
          ('steady_limb','Steady','略增厚的木钢弓臂，保留原有长弓轮廓。')]:
        part('riser',key,'SK_WoodSteelLongbow_'+suffix,appearance=appearance)
    part('grip','false','SM_WoodSteelLongbow_Grip','原装旧革缠带','从原弓分离的旧革缠带，沿用原有掌心接触位置。','深色旧革斜绕握面。')
    for key,suffix,appearance in [('waxed_linen','Linen','深棕蜡麻包面，纤维细纹沿原有缠绕结构延伸。'),
          ('woven_linen_grip','Linen','暖棕麻布包面，交错织纹覆盖原有缠绕结构。'),
          ('slim_leather_grip','SlimLeather','略薄的旧革斜绕握面。'),('padded_leather_grip','PaddedLeather','略厚的软革握面，沿用原有斜绕纹路。')]:
        extra={'bow_part_grip_material':asset('M_WoodSteelLongbow_'+('WaxedLinen' if key=='waxed_linen' else 'Linen')+'_Static')} if suffix=='Linen' else None
        part('grip',key,'SM_WoodSteelLongbow_Grip_'+suffix,appearance=appearance,extra=extra)
    part('arrow_rest','false','SM_WoodSteelLongbow_Rest','原装金属箭台','原模型箭台转向持弓侧，并按箭杆高度对齐。','与握把上方护片贴合的侧置金属箭台。')
    for key,suffix,appearance in [('lined_rest','Lined','原装金属箭台增加深棕皮垫。'),
          ('open_quick_rest','Quick','金属箭台增加敞口磨光滑片。'),
          ('fork_guide_rest','Fork','金属箭台增加带皮衬的双侧导向托面。')]:
        part('arrow_rest',key,'SM_WoodSteelLongbow_Rest_'+suffix,appearance=appearance,extra={'arrow_rest_cm':vec(manifest['arrow_rest_cm'])})
    part('sight','false','','不安装瞄具',
         '沿箭杆方向瞄准。','保留弓身原貌，不附加瞄圈和底座。',
         {'bow_ads_sight_cm':'','bow_ads_rest_cm':'63,10,-12','bow_scope_magnification':1})
    for key,suffix,mag in [('bow_clearfield_2x','2x',2),('bow_farwatch_4x','4x',4)]:
        part('sight',key,'SM_WoodSteelLongbow_Optic'+suffix,appearance='贴合原弓金属护片的钢座与支臂，保留单片玻璃和原有刻线。',
             extra={'bow_ads_sight_cm':vec(manifest['optic_aim_center_cm']),
                    'bow_ads_sight_distance_cm':manifest['optic_eye_distance_cm'],'bow_scope_magnification':mag})
    d['weapons']=[x for x in d['weapons'] if x['id']!='bow_woodsteel']+[w]
edit_json('bow-gunsmith',gunsmith)
def recipe(d):
    r=copy.deepcopy(next(x for x in d['recipes'] if x['id']=='woodwork_bow'))
    r.update(id='woodwork_bow_woodsteel',output={'item':'bow_woodsteel','count':1})
    r['inputs'].append({'item':'ironIngot','count':2})
    d['recipes']=[x for x in d['recipes'] if x['id']!=r['id']]+[r]
edit_json('woodworking-recipes',recipe)
def pattern(d):
    p=copy.deepcopy(next(x for x in d['patterns'] if x['id']=='bow_limb'))
    p.update(id='bow_woodsteel_limb',name='弓 · 高地长弓',craftRecipe='woodwork_bow_woodsteel',
        description='加工长木弓胎并装配金属结构，加工达标后返回工作面板领取高地长弓。')
    d['patterns']=[x for x in d['patterns'] if x['id']!=p['id']]+[p]
edit_json('woodworking',pattern)
ini=project/'Config/DefaultGame.ini';raw=ini.read_bytes();s=raw.decode('utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/WoodSteelLongbow20261026")'
if line not in s:
    newline='\r\n' if '\r\n' in s else '\n'
    header='[/Script/UnrealEd.ProjectPackagingSettings]'
    s=s.replace(header,header+newline+line,1)
    if ini.read_bytes()!=raw:raise RuntimeError('Cook configuration changed during edit')
    (before/ini.name).write_bytes(raw)
    ini.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+s.encode('utf-8'));saved.append(str(ini))
(P/'catalog-install.json').write_text(json.dumps({'weapon':'bow_woodsteel','files':saved,'backup':str(before),'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('WOOD_STEEL_LONGBOW_CATALOG_INSTALLED')
