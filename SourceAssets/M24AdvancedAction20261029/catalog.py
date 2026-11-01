import copy
ID='m24_advanced_action'
OPTIONS=[dict(id='false',name='M24 原装枪身',description='原装一体式枪托与前护木，保留原有握持轮廓。',stats={},effects=[]),
 dict(id=ID,name='先进枪机系统',description='重构机匣、弹匣口与完整上下护木的金属底盘，配有镂空散热槽、连续导轨与沉孔紧固件，沿用原装枪托。',
      stats={'recoil_mult':.85,'stability_mult':1.2,'ads_percent':.10},
      effects=[{'text':'后坐力-15%','benefit':1},{'text':'稳定性+20%','benefit':1},{'text':'开镜耗时+10%','benefit':-1}])]
def apply_catalog(data):
    if 'body' not in data['slots']:
        data['slots'].append('body');data['categories'].append('枪身主体');data['defaults'].append('原装枪身')
    row=next(w for w in data['weapons'] if w['id']=='ue_m24')
    if 'body' not in row['allowed']:row['allowed'].append('body')
    row['default_parts']['body']='false';row['options']['body']=copy.deepcopy(OPTIONS)
    for option in row['options'].get('stock',[]):
        if option['id']=='m24_cheekrest':
            option['name']='M24 原装贴腮板';option['description']='贴合原装后托上缘的独立弧形贴腮板。'
        elif option['id']=='none':option['description']='移除当前枪身的贴腮板，保留枪托。'
