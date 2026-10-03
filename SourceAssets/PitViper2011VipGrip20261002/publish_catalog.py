"""Publish the exclusive Viper grip and its user-defined hip-spread modifier."""
import copy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
ID='ue_pit_viper2011';PART='pit_viper_vip_scales';D='/Game/Weapons/PitViper2011/VipGrip20261002'
OPTION={'id':PART,'name':'蝮蛇防滑纹',
    'description':'2011 的 VIP 专属握把表面。石墨黑细鳞纹沿握把左右两侧自上而下延伸，细边贴合原厂轮廓，下沿避开弹匣接口与底部扩口。',
    'effects':[{'text':'腰射随机散布减少15%','benefit':1}],
    'stats':{'hip_spread_mult':.85}}

def augment_weapon(weapon,catalog):
    binding=weapon['pistol_grip_surface']
    binding.setdefault('variants',{})[PART]={'mesh':D+'/SM_PitViper2011_VipViperGrip',
        'material':D+'/Materials/M_PitViper2011_VipViperGrip'}
    exclusive=[copy.deepcopy(v) for v in binding.get('exclusive_options',[]) if v['id']!=PART]
    exclusive.append(copy.deepcopy(OPTION));binding['exclusive_options']=exclusive
    weapon['options']['reargrip']=copy.deepcopy(catalog['pistol_grip_surface_options'])+copy.deepcopy(exclusive)
    if 'reargrip' not in weapon['allowed']:weapon['allowed'].append('reargrip')
    finish=O.parent/'PitViper2011SurfaceRefine20261003'
    if (finish/'import_receipt.json').exists() and json.loads((finish/'import_receipt.json').read_text(encoding='utf8')).get('status')=='imported_and_saved':
        import importlib.util
        spec=importlib.util.spec_from_file_location('pit_viper_surface_contract',finish/'surface_contract.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        weapon=module.augment_weapon(weapon)
    return weapon

def publish():
    path=P/'Content/ColdSteelData/gunsmith.json'
    text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
    weapon=augment_weapon(copy.deepcopy(next(w for w in catalog['weapons'] if w['id']==ID)),catalog)
    pos=text.index(json.dumps(ID),text.index('"weapons"'));start=text.rfind('{',0,pos)
    _,size=json.JSONDecoder().raw_decode(text[start:])
    result=text[:start]+json.dumps(weapon,ensure_ascii=False,indent=2)+text[start+size:]
    if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve concurrent catalog publication')
    path.write_text(result,encoding='utf8')
    record={'weapon':ID,'part':PART,'slot':'reargrip','option':OPTION,
        'binding':weapon['pistol_grip_surface']['variants'][PART],
        'scope':'single, dual, staff offhand via existing surface configuration and inventory parts',
        'kind':'VIP themed exclusive grip with user-defined hip-spread reduction, 2026-10-03',
        'game_tested':False}
    (O/'catalog.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print('VIP_VIPER_GRIP_CATALOG_PUBLISHED',flush=True)

if __name__=='__main__':publish()
