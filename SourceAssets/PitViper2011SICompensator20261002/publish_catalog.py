"""Publish SI as an exclusive 2011 muzzle with the user-defined modifiers."""
import copy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];ID='ue_pit_viper2011';PART='pit_viper_si_compensator'
D='/Game/Weapons/PitViper2011/SICompensator20261003'
def augment_weapon(weapon,catalog):
    baseline=next(v for v in weapon['options']['muzzle'] if v['id']=='brake')
    option=copy.deepcopy(baseline)
    option.update(id=PART,name='SI 枪口补偿器',limited=True,
        description='2011 限定枪口补偿器。方形切面外壳配顶部排气槽和侧孔，替换原厂补偿段，保留枪管、准星与机械联动。',
        stats={'ads_percent':-.10,'recoil_mult':.90,'stability_mult':1.05,'hip_spread_mult':.80},
        effects=[{'text':'开镜耗时减少10%','benefit':1},
                 {'text':'后坐力降低10%','benefit':1},
                 {'text':'枪械稳定性提高5%','benefit':1},
                 {'text':'腰射随机散布减少20%','benefit':1}])
    choices=[v for v in weapon['options']['muzzle'] if v['id']!=PART];choices.append(option)
    weapon['options']['muzzle']=choices
    if 'muzzle' not in weapon['allowed']:weapon['allowed'].append('muzzle')
    return weapon
def publish():
    receipt_path=O/'integration_receipt.json';receipt=json.loads(receipt_path.read_text(encoding='utf8'))
    if receipt.get('status')!='imported_and_saved':raise RuntimeError('Save SI assets before publishing')
    path=P/'Content/ColdSteelData/gunsmith.json';text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
    weapon=augment_weapon(copy.deepcopy(next(w for w in catalog['weapons'] if w['id']==ID)),catalog)
    pos=text.index(json.dumps(ID),text.index('"weapons"'));start=text.rfind('{',0,pos)
    _,size=json.JSONDecoder().raw_decode(text[start:])
    result=text[:start]+json.dumps(weapon,ensure_ascii=False,indent=2)+text[start+size:]
    if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve concurrent catalog changes')
    path.write_text(result,encoding='utf8')
    option=next(v for v in weapon['options']['muzzle'] if v['id']==PART)
    (O/'catalog.json').write_text(json.dumps({'weapon':ID,'part':PART,'slot':'muzzle','option':option,
       'mesh':D+'/SM_PitViper2011_SICompensator','limited':True,'balance':'user-defined SI modifiers, 2026-10-03',
       'game_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
    receipt['catalog_published']=True;receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print('PIT_VIPER_SI_COMPENSATOR_CATALOG_PUBLISHED',flush=True)
if __name__=='__main__':publish()
