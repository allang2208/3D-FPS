"""M24-only bolt action option; the existing shot clock owns all cycle timing."""
import copy
ID='m24_carbon_light_bolt'
OPTIONS=[dict(id='false',name='M24 原装栓机',description='原装金属栓体、拉柄与尾帽，保留原有机械表面。',stats={},effects=[],special_effects=[]),
 dict(id=ID,name='碳纤维轻型栓机',description='沿用原装栓机轮廓与拉柄，外覆细密斜纹碳纤维，保留金属端面与接合环。',
      stats={'fire_interval_mult':1/1.30},effects=[{'text':'拉栓速度+30%','benefit':1}],
      special_effects=['轻型栓机｜拉栓速度+30%，同步缩短射击间隔；换弹和装备动作保持原有节奏。'])]
def apply(row):
    if 'bolt' not in row['allowed']:row['allowed'].append('bolt')
    row['default_parts']['bolt']='false';row['options']['bolt']=copy.deepcopy(OPTIONS)
def apply_catalog(data):
    if 'bolt' not in data['slots']:
        data['slots'].append('bolt');data['categories'].append('栓机');data['defaults'].append('原装栓机')
    apply(next(x for x in data['weapons'] if x['id']=='ue_m24'))
