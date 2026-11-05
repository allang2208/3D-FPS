import copy
ID='m24_advanced_action'
TACTICAL_INTERFACE='战术挂件接口｜安装后解锁一个战术挂件槽，可安装通用镭射或手电；切回原厂枪身时自动撤下战术挂件。'
OPTIONS=[dict(id='false',name='M24 原装枪身',description='原装一体式枪托与前护木，保留原有握持轮廓。',stats={},effects=[]),
 dict(id=ID,name='先进枪机系统',description='重构机匣、弹匣口与完整上下护木的金属底盘，配有镂空散热槽、连续导轨与沉孔紧固件，沿用原装枪托。',
      stats={'recoil_mult':.85,'stability_mult':1.2},
      effects=[{'text':'后坐力-15%','benefit':1},{'text':'稳定性+20%','benefit':1}],
      special_effects=['后握把接口｜安装后解锁后握把改造；切回原厂枪身时自动撤下后握把改造。',TACTICAL_INTERFACE])]

def apply_tactical(data,row):
    if 'tactical' not in row['allowed']:row['allowed'].append('tactical')
    row['default_parts']['tactical']='false'
    common=next(w for w in data['weapons'] if w['id']=='ue_m4a1')['options']['tactical']
    options=copy.deepcopy(common)
    for option in data.get('common_options',{}).get('tactical',[]):
        if not any(o['id']==option['id'] for o in options):options.append(copy.deepcopy(option))
    row['options']['tactical']=options
    for option in row['options']['body']:
        if option['id']==ID and TACTICAL_INTERFACE not in option.setdefault('special_effects',[]):
            option['special_effects'].append(TACTICAL_INTERFACE)
    trait='安装先进枪机系统后解锁后握把和一个战术挂件槽；换回原厂枪身会自动撤下依赖改造。'
    if not any(t.get('text')==trait for t in row.setdefault('traits',[])):
        row['traits'].append({'icon':'mechanic','text':trait})
def apply_catalog(data):
    if 'body' not in data['slots']:
        data['slots'].append('body');data['categories'].append('枪身主体');data['defaults'].append('原装枪身')
    row=next(w for w in data['weapons'] if w['id']=='ue_m24')
    if 'body' not in row['allowed']:row['allowed'].append('body')
    row['default_parts']['body']='false';row['options']['body']=copy.deepcopy(OPTIONS)
    apply_tactical(data,row)
    for option in row['options'].get('stock',[]):
        if option['id']=='m24_cheekrest':
            option['name']='M24 原装贴腮板';option['description']='贴合原装后托上缘的独立弧形贴腮板。'
        elif option['id']=='none':option['description']='移除当前枪身的贴腮板，保留枪托。'
